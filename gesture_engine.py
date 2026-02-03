"""
GESTURE ENGINE - Computer Vision Layer
Handles webcam, MediaPipe AI, hand tracking, and gesture recognition
"""

import cv2
import numpy as np
from collections import deque
import time
import config

# Try importing MediaPipe with compatibility for different versions
try:
    import mediapipe as mp
    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils
    mp_drawing_styles = mp.solutions.drawing_styles
except AttributeError:
    from mediapipe import solutions
    mp_hands = solutions.hands
    mp_drawing = solutions.drawing_utils
    mp_drawing_styles = solutions.drawing_styles


class GestureEngine:
    """Main gesture detection and tracking engine"""
    
    def __init__(self):
        print("🚀 Initializing Gesture Engine...")
        
        # Initialize MediaPipe Hands
        self.hands = mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=config.MP_MAX_HANDS,
            min_detection_confidence=config.MP_MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=config.MP_MIN_TRACKING_CONFIDENCE,
            model_complexity=config.MP_MODEL_COMPLEXITY
        )
        
        # Smoothing buffers
        self.landmark_buffer = {}
        self.position_history = deque(maxlen=config.LANDMARK_BUFFER_SIZE)
        
        # Gesture state tracking
        self.current_gesture = "none"
        self.previous_gesture = "none"
        self.gesture_start_time = 0
        self.last_gesture_time = 0
        
        # Swipe detection
        self.swipe_start_pos = None
        self.swipe_start_time = None
        
        # Pinch tracking
        self.previous_pinch_distance = None
        self.pinch_baseline = None
        
        # Depth tracking for perspective compensation
        self.hand_depth = None
        self.depth_history = deque(maxlen=5)
        
        # Performance metrics
        self.fps_history = deque(maxlen=30)
        self.jitter_history = deque(maxlen=30)
        
        print("✅ Gesture Engine Ready!")
    
    def calculate_distance(self, point1, point2):
        """Calculate Euclidean distance between two landmarks"""
        return np.sqrt((point1.x - point2.x)**2 + 
                      (point1.y - point2.y)**2 + 
                      (point1.z - point2.z)**2)
    
    def calculate_distance_cm(self, point1, point2, hand_depth):
        """Calculate real-world distance in centimeters"""
        # Rough approximation: normalize by depth
        pixel_distance = np.sqrt((point1.x - point2.x)**2 + (point1.y - point2.y)**2)
        # Scale based on depth (closer = larger pixels per cm)
        depth_factor = hand_depth / 30.0  # Normalize around 30cm
        distance_cm = pixel_distance * 100 * depth_factor
        return distance_cm
    
    def smooth_landmarks(self, hand_landmarks, hand_id=0):
        """Apply temporal smoothing to reduce jitter"""
        if hand_id not in self.landmark_buffer:
            self.landmark_buffer[hand_id] = {i: deque(maxlen=config.LANDMARK_BUFFER_SIZE) 
                                            for i in range(21)}
        
        # Store current landmarks
        for idx, landmark in enumerate(hand_landmarks.landmark):
            self.landmark_buffer[hand_id][idx].append([landmark.x, landmark.y, landmark.z])
        
        # Calculate smoothed positions using exponential moving average
        smoothed_landmarks = []
        for idx in range(21):
            if len(self.landmark_buffer[hand_id][idx]) > 0:
                positions = np.array(self.landmark_buffer[hand_id][idx])
                # Apply exponential moving average
                weights = np.exp(np.linspace(-2, 0, len(positions)))
                weights /= weights.sum()
                avg_pos = np.average(positions, axis=0, weights=weights)
                smoothed_landmarks.append(avg_pos)
            else:
                landmark = hand_landmarks.landmark[idx]
                smoothed_landmarks.append([landmark.x, landmark.y, landmark.z])
        
        return smoothed_landmarks
    
    def estimate_hand_depth(self, hand_landmarks):
        """Estimate hand depth (Z-axis) for perspective compensation"""
        # Use the distance between wrist and middle finger MCP as depth indicator
        wrist = hand_landmarks.landmark[0]
        middle_mcp = hand_landmarks.landmark[9]
        
        # Calculate hand "span" - larger span = closer to camera
        hand_span = self.calculate_distance(wrist, middle_mcp)
        
        # Convert to approximate depth in cm (calibrated empirically)
        # This is a rough inverse relationship
        estimated_depth = 30.0 / (hand_span * 50)  # Rough calibration
        estimated_depth = np.clip(estimated_depth, config.MIN_DEPTH_CM, config.MAX_DEPTH_CM)
        
        # Smooth depth estimates
        self.depth_history.append(estimated_depth)
        smoothed_depth = np.mean(self.depth_history)
        
        return smoothed_depth
    
    def detect_fist(self, hand_landmarks):
        """Detect if hand is in a fist configuration"""
        # Check if all fingertips are close to palm
        palm_center = hand_landmarks.landmark[0]  # Wrist as reference
        
        fingertips = [4, 8, 12, 16, 20]  # Thumb, Index, Middle, Ring, Pinky tips
        finger_bases = [2, 5, 9, 13, 17]  # Base of each finger
        
        fingers_closed = 0
        for tip_idx, base_idx in zip(fingertips, finger_bases):
            tip = hand_landmarks.landmark[tip_idx]
            base = hand_landmarks.landmark[base_idx]
            
            # Check if fingertip is below or at the base (closed)
            if tip.y >= base.y - 0.02:  # Small threshold for tolerance
                fingers_closed += 1
        
        # Need at least 4 fingers closed to count as fist
        return fingers_closed >= 4
    
    def detect_pinch(self, hand_landmarks):
        """Detect pinch gesture and measure distance between thumb and index"""
        thumb_tip = hand_landmarks.landmark[4]
        index_tip = hand_landmarks.landmark[8]
        
        # Calculate distance in normalized coordinates
        pinch_distance = self.calculate_distance(thumb_tip, index_tip)
        
        # Convert to cm using depth estimation
        depth = self.hand_depth if self.hand_depth else 30.0
        pinch_distance_cm = self.calculate_distance_cm(thumb_tip, index_tip, depth)
        
        # Check if it's a valid pinch (fingers close enough)
        is_pinching = pinch_distance_cm < config.PINCH_MAX_DISTANCE
        
        return is_pinching, pinch_distance_cm
    
    def detect_swipe(self, hand_landmarks, current_time):
        """Detect horizontal swipe gestures"""
        # Use palm center (wrist) for swipe detection
        palm = hand_landmarks.landmark[0]
        current_pos = np.array([palm.x, palm.y])
        
        # Initialize swipe tracking
        if self.swipe_start_pos is None:
            self.swipe_start_pos = current_pos
            self.swipe_start_time = current_time
            return None
        
        # Calculate displacement
        displacement = current_pos - self.swipe_start_pos
        time_elapsed = current_time - self.swipe_start_time
        
        # Calculate velocity
        if time_elapsed > 0:
            velocity = np.linalg.norm(displacement) / time_elapsed
        else:
            velocity = 0
        
        # Convert displacement to cm (rough approximation)
        depth = self.hand_depth if self.hand_depth else 30.0
        displacement_cm = np.linalg.norm(displacement) * 100 * (depth / 30.0)
        
        swipe_detected = None
        
        # Check for horizontal swipe
        if displacement_cm > config.SWIPE_THRESHOLD_CM and velocity > config.SWIPE_MIN_VELOCITY:
            if abs(displacement[0]) > abs(displacement[1]) * 2:  # More horizontal than vertical
                if displacement[0] > 0:
                    swipe_detected = "swipe_right"
                else:
                    swipe_detected = "swipe_left"
                
                # Reset swipe tracking
                self.swipe_start_pos = current_pos
                self.swipe_start_time = current_time
        
        # Reset if too much time has passed
        if time_elapsed > 1.0:
            self.swipe_start_pos = current_pos
            self.swipe_start_time = current_time
        
        return swipe_detected
    
    def detect_gesture(self, hand_landmarks, current_time):
        """Main gesture detection pipeline"""
        gesture = "none"
        gesture_data = {}
        
        # Update hand depth
        self.hand_depth = self.estimate_hand_depth(hand_landmarks)
        gesture_data['depth'] = self.hand_depth
        
        # Priority 1: Check for fist (highest priority for play/pause)
        if self.detect_fist(hand_landmarks):
            gesture = "fist"
            gesture_data['confidence'] = config.FIST_CONFIDENCE_THRESHOLD
        
        # Priority 2: Check for pinch (volume control)
        else:
            is_pinching, pinch_distance = self.detect_pinch(hand_landmarks)
            if is_pinching:
                gesture = "pinch"
                gesture_data['pinch_distance'] = pinch_distance
                
                # Detect pinch movement direction
                if self.previous_pinch_distance is not None:
                    distance_delta = pinch_distance - self.previous_pinch_distance
                    
                    if abs(distance_delta) > config.PINCH_DEADZONE_CM:
                        if distance_delta > 0:
                            gesture = "pinch_open"  # Volume up
                            gesture_data['volume_delta'] = distance_delta
                        else:
                            gesture = "pinch_close"  # Volume down
                            gesture_data['volume_delta'] = distance_delta
                
                self.previous_pinch_distance = pinch_distance
            else:
                self.previous_pinch_distance = None
        
        # Priority 3: Check for swipe (track navigation)
        if gesture == "none":
            swipe = self.detect_swipe(hand_landmarks, current_time)
            if swipe:
                gesture = swipe
        
        return gesture, gesture_data
    
    def check_gesture_cooldown(self, current_time):
        """Check if enough time has passed since last gesture"""
        return (current_time - self.last_gesture_time) >= config.GESTURE_COOLDOWN
    
    def update_gesture_state(self, gesture, current_time):
        """Update gesture state with hold time validation"""
        # If gesture changed, reset timer
        if gesture != self.current_gesture:
            self.current_gesture = gesture
            self.gesture_start_time = current_time
            return None  # Not held long enough yet
        
        # Check if gesture has been held long enough
        hold_duration = current_time - self.gesture_start_time
        if hold_duration >= config.GESTURE_HOLD_TIME:
            # Check cooldown
            if self.check_gesture_cooldown(current_time):
                self.last_gesture_time = current_time
                return gesture
        
        return None  # Gesture not confirmed yet
    
    def calculate_jitter(self, current_pos):
        """Calculate cursor jitter in pixels"""
        self.position_history.append(current_pos)
        
        if len(self.position_history) < 2:
            return 0
        
        positions = np.array(self.position_history)
        variance = np.var(positions, axis=0)
        jitter = np.sqrt(np.sum(variance))
        
        self.jitter_history.append(jitter)
        return np.mean(self.jitter_history)
    
    def draw_visualization(self, image, hand_landmarks, smoothed_data, gesture, gesture_data, fps, jitter):
        """Draw all visual feedback on the frame"""
        h, w, c = image.shape
        
        # Draw skeleton if enabled
        if config.SHOW_SKELETON:
            connections = mp_hands.HAND_CONNECTIONS
            
            for connection in connections:
                start_idx, end_idx = connection
                
                if smoothed_data:
                    start_point = smoothed_data[start_idx]
                    end_point = smoothed_data[end_idx]
                    start_pos = (int(start_point[0] * w), int(start_point[1] * h))
                    end_pos = (int(end_point[0] * w), int(end_point[1] * h))
                else:
                    start_landmark = hand_landmarks.landmark[start_idx]
                    end_landmark = hand_landmarks.landmark[end_idx]
                    start_pos = (int(start_landmark.x * w), int(start_landmark.y * h))
                    end_pos = (int(end_landmark.x * w), int(end_landmark.y * h))
                
                cv2.line(image, start_pos, end_pos, config.COLOR_SKELETON, 3)
            
            # Draw landmarks
            for idx, landmark in enumerate(hand_landmarks.landmark):
                if smoothed_data:
                    pos = smoothed_data[idx]
                    cx, cy = int(pos[0] * w), int(pos[1] * h)
                else:
                    cx, cy = int(landmark.x * w), int(landmark.y * h)
                
                if idx in [0, 4, 8, 12, 16, 20]:  # Key joints
                    cv2.circle(image, (cx, cy), 8, config.COLOR_FINGERTIPS, -1)
                    cv2.circle(image, (cx, cy), 10, config.COLOR_TEXT, 2)
                else:
                    cv2.circle(image, (cx, cy), 5, config.COLOR_JOINTS, -1)
                    cv2.circle(image, (cx, cy), 7, config.COLOR_TEXT, 2)
        
        # Draw gesture name
        if config.SHOW_GESTURE_NAME and gesture != "none":
            gesture_display = gesture.replace("_", " ").upper()
            cv2.putText(image, gesture_display, (w//2 - 100, 100),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.2, config.COLOR_ACTION, 3)
        
        # Draw metrics
        if config.SHOW_METRICS:
            y_offset = 30
            metrics = [
                f"FPS: {fps:.1f}",
                f"Jitter: {jitter:.2f}px",
                f"Depth: {gesture_data.get('depth', 0):.1f}cm",
            ]
            
            for metric in metrics:
                cv2.putText(image, metric, (10, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, config.COLOR_TEXT, 2)
                y_offset += 25
        
        # Draw pinch distance if pinching
        if 'pinch_distance' in gesture_data and config.SHOW_VOLUME_BAR:
            pinch_dist = gesture_data['pinch_distance']
            bar_width = int((pinch_dist / config.PINCH_MAX_DISTANCE) * 200)
            cv2.rectangle(image, (w - 220, h - 50), (w - 20 + bar_width, h - 30),
                         config.COLOR_ACTION, -1)
            cv2.putText(image, f"Vol: {pinch_dist:.1f}cm", (w - 220, h - 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, config.COLOR_TEXT, 2)
        
        return image
    
    def process_frame(self, frame):
        """Process a single frame and return gesture information"""
        current_time = time.time()
        
        # Convert to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process with MediaPipe
        results = self.hands.process(frame_rgb)
        
        gesture = "none"
        gesture_data = {}
        confirmed_gesture = None
        
        if results.multi_hand_landmarks:
            hand_landmarks = results.multi_hand_landmarks[0]  # Use first hand
            
            # Smooth landmarks
            smoothed = self.smooth_landmarks(hand_landmarks)
            
            # Detect gesture
            gesture, gesture_data = self.detect_gesture(hand_landmarks, current_time)
            
            # Update state and check if gesture should be confirmed
            confirmed_gesture = self.update_gesture_state(gesture, current_time)
            
            # Calculate jitter
            palm_pos = [hand_landmarks.landmark[0].x * frame.shape[1],
                       hand_landmarks.landmark[0].y * frame.shape[0]]
            jitter = self.calculate_jitter(palm_pos)
            
            # Draw visualization
            fps = 1.0 / (current_time - self.last_gesture_time) if (current_time - self.last_gesture_time) > 0 else 0
            frame = self.draw_visualization(frame, hand_landmarks, smoothed, 
                                          gesture, gesture_data, fps, jitter)
        
        return frame, confirmed_gesture, gesture_data
    
    def cleanup(self):
        """Clean up resources"""
        self.hands.close()