import cv2
import numpy as np
import time
import config
import mediapipe as mp
from collections import deque

class GestureEngine:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(model_complexity=0, min_detection_confidence=0.8, min_tracking_confidence=0.8)
        
        # Smoothing Buffers
        self.y_buffer = deque(maxlen=5)
        self.x_buffer = deque(maxlen=5)
        
        # State tracking
        self.last_action_time = 0
        self.fist_start_time = None
        self.volume_anchor_y = None 
        self.active_mode = "none" # 'volume', 'slide', or 'none'

    def is_v_sign(self, landmarks):
        """Sharpened detection: Index and Middle clearly extended, others curled"""
        index_up = landmarks.landmark[8].y < landmarks.landmark[6].y
        middle_up = landmarks.landmark[12].y < landmarks.landmark[10].y
        ring_down = landmarks.landmark[16].y > landmarks.landmark[14].y
        pinky_down = landmarks.landmark[20].y > landmarks.landmark[18].y
        
        # V-Shape check: Index and Middle should have horizontal distance
        v_gap = abs(landmarks.landmark[8].x - landmarks.landmark[12].x)
        
        return index_up and middle_up and ring_down and pinky_down and v_gap > 0.02

    def process_frame(self, frame):
        h, w = frame.shape[:2]
        current_time = time.time()
        
        # Performance processing
        small_frame = cv2.resize(frame, (640, 360))
        results = self.hands.process(cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB))
        
        gesture = "none"
        gesture_data = {}
        
        if results.multi_hand_landmarks:
            landmarks = results.multi_hand_landmarks[0]
            if config.SHOW_SKELETON:
                self.mp_drawing.draw_landmarks(frame, landmarks, self.mp_hands.HAND_CONNECTIONS)

            # --- MODE SELECTION & LOCKING ---
            dist_pinch = np.sqrt((landmarks.landmark[4].x - landmarks.landmark[8].x)**2 + 
                                 (landmarks.landmark[4].y - landmarks.landmark[8].y)**2)
            is_v = self.is_v_sign(landmarks)
            is_pinch = dist_pinch < 0.06 and not is_v
            
            # --- SHARPENED V-SIGN FLICK ---
            if is_v and self.active_mode != "volume":
                self.active_mode = "slide"
                
                # Track the Index Tip (Landmark 8) for maximum "snap"
                curr_x = landmarks.landmark[8].x
                self.x_buffer.append(curr_x)
                
                if len(self.x_buffer) == 5 and current_time - self.last_action_time > 0.6:
                    diff_x = self.x_buffer[-1] - self.x_buffer[0]
                    
                    # ULTRA-SENSITIVE NEXT
                    if diff_x > 0.12: 
                        gesture = "swipe_right"
                        self.last_action_time = current_time
                        self.x_buffer.clear()
                    
                    # ULTRA-SENSITIVE PREVIOUS (lowered from -0.18 for instant response)
                    elif diff_x < -0.10:
                        gesture = "swipe_left"
                        self.last_action_time = current_time
                        self.x_buffer.clear()
                
                # Visual Handle (Cyan for V-Sign)
                p1 = (int(landmarks.landmark[8].x * w), int(landmarks.landmark[8].y * h))
                p2 = (int(landmarks.landmark[12].x * w), int(landmarks.landmark[12].y * h))
                cv2.line(frame, p1, p2, (255, 255, 0), 4)
            
            # --- 2. POLISHED VOLUME SLIDER (Pinch) ---
            elif is_pinch and self.active_mode != "slide":
                self.active_mode = "volume"
                curr_y = landmarks.landmark[8].y
                if self.volume_anchor_y is None: self.volume_anchor_y = curr_y
                
                # Visual Rail
                hand_x = int(landmarks.landmark[8].x * w)
                anchor_y = int(self.volume_anchor_y * h)
                cv2.line(frame, (hand_x, anchor_y - 100), (hand_x, anchor_y + 100), (0, 255, 0), 1)
                cv2.circle(frame, (hand_x, int(curr_y * h)), 12, (0, 255, 0), -1)

                self.y_buffer.append(curr_y)
                if len(self.y_buffer) == 5:
                    avg_y_diff = self.volume_anchor_y - np.mean(self.y_buffer)
                    if abs(avg_y_diff) > 0.05:
                        gesture = "pinch_open" if avg_y_diff > 0 else "pinch_close"
                        gesture_data['volume_delta'] = avg_y_diff * 200
            
            # --- 3. POLISHED FIST (Play/Pause) ---
            else:
                self.active_mode = "none"
                self.volume_anchor_y = None
                self.x_buffer.clear()
                self.y_buffer.clear()
                
                tips = [8, 12, 16, 20]; bases = [6, 10, 14, 18]
                if all(landmarks.landmark[t].y > landmarks.landmark[b].y for t, b in zip(tips, bases)):
                    if self.fist_start_time is None: self.fist_start_time = current_time
                    elapsed = current_time - self.fist_start_time
                    # Glow Effect
                    radius = int(max(1, 50 * min(elapsed/1.5, 1.0)))
                    cv2.circle(frame, (int(landmarks.landmark[0].x * w), int(landmarks.landmark[0].y * h)), radius, (0, 255, 255), 2)
                    if elapsed >= 1.5:
                        gesture = "fist"
                        self.fist_start_time = current_time + 2.0
                else: self.fist_start_time = None

            if config.SHOW_GESTURE_NAME and gesture != "none":
                cv2.putText(frame, f"COMMAND: {gesture.upper()}", (10, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

        return frame, gesture, gesture_data

    def cleanup(self):
        self.hands.close()

