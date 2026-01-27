import cv2
import mediapipe as mp
import pyautogui
import math
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# --- 1. MANUAL SKELETON MAP ---
# Defines which landmarks to connect with lines
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),    # Thumb
    (0, 5), (5, 6), (6, 7), (7, 8),    # Index
    (0, 9), (9, 10), (10, 11), (11, 12), # Middle
    (0, 13), (13, 14), (14, 15), (15, 16), # Ring
    (0, 17), (17, 18), (18, 19), (19, 20), # Pinky
    (5, 9), (9, 13), (13, 17)          # Palm
]

# --- 2. CONFIG & STABILITY ---
SCREEN_WIDTH, SCREEN_HEIGHT = pyautogui.size()
pyautogui.FAILSAFE = True
prev_x, prev_y = 0, 0
smoothing_alpha = 0.2  # Lower = smoother, Higher = more responsive
deadzone_px = 6        # Stops the "shaking" when hand is still

# --- 3. INITIALIZE AI (STRICTER CONFIDENCE) ---
base_options = python.BaseOptions(model_asset_path='hand_landmarker.task')
options = vision.HandLandmarkerOptions(
    base_options=base_options,
    num_hands=1,
    min_hand_detection_confidence=0.8,
    min_hand_presence_confidence=0.6,
    min_tracking_confidence=0.6
)
detector = vision.HandLandmarker.create_from_options(options)

cap = cv2.VideoCapture(0)

while cap.isOpened():
    success, frame = cap.read()
    if not success: break
    
    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape
    
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
    result = detector.detect(mp_image)

    if result.hand_landmarks:
        hand = result.hand_landmarks[0]
        
        # --- GESTURE: FIST DETECTION ---
        # Logic: Are the finger tips lower than the second knuckle?
        is_fist = (hand[8].y > hand[6].y and 
                   hand[12].y > hand[10].y and 
                   hand[16].y > hand[14].y and 
                   hand[20].y > hand[18].y)

        # --- DRAWING THE HUD (Skeleton) ---
        color = (0, 255, 0) if not is_fist else (0, 0, 255) # Green normally, Red for Fist
        
        # Draw connections
        for connection in HAND_CONNECTIONS:
            p1 = (int(hand[connection[0]].x * w), int(hand[connection[0]].y * h))
            p2 = (int(hand[connection[1]].x * w), int(hand[connection[1]].y * h))
            cv2.line(frame, p1, p2, (255, 255, 255), 2)
        
        # Draw joints
        for lm in hand:
            cv2.circle(frame, (int(lm.x * w), int(lm.y * h)), 4, color, -1)

        # --- INTERACTION ENGINE ---
        if is_fist:
            cv2.putText(frame, "FIST: SELECTED", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
            # pyautogui.click() # This fires a mouse click
        else:
            # 1. RAW COORDINATES
            raw_x = hand[8].x * SCREEN_WIDTH
            raw_y = hand[8].y * SCREEN_HEIGHT

            # 2. STABILITY (DEADZONE + SMOOTHING)
            distance = math.sqrt((raw_x - prev_x)**2 + (raw_y - prev_y)**2)
            
            if distance > deadzone_px:
                curr_x = prev_x + (raw_x - prev_x) * smoothing_alpha
                curr_y = prev_y + (raw_y - prev_y) * smoothing_alpha
                
                pyautogui.moveTo(int(curr_x), int(curr_y), _pause=False)
                prev_x, prev_y = curr_x, curr_y

    cv2.imshow('Holographic Spotify Controller', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()