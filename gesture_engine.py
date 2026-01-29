import cv2
import mediapipe as mp
import math
import time
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from spotify_controller import SpotifyController, MouseController

# --- 1. SKELETON CONNECTION MAP ---
# This defines which dots connect to make the hand/arm look
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),    # Thumb
    (0, 5), (5, 6), (6, 7), (7, 8),    # Index
    (0, 9), (9, 10), (10, 11), (11, 12), # Middle
    (0, 13), (13, 14), (14, 15), (15, 16), # Ring
    (0, 17), (17, 18), (18, 19), (19, 20), # Pinky
    (5, 9), (9, 13), (13, 17), (0, 17), (0, 5) # Palm base
]

# --- 2. CONFIG ---
ZONE_MARGIN = 0.2
p_time = 0

# --- 3. INITIALIZE AI ---
base_options = python.BaseOptions(model_asset_path='hand_landmarker.task')
options = vision.HandLandmarkerOptions(
    base_options=base_options,
    num_hands=1,
    min_hand_detection_confidence=0.7,
    min_hand_presence_confidence=0.2, 
    min_tracking_confidence=0.2
)
detector = vision.HandLandmarker.create_from_options(options)

spotify = SpotifyController()
my_controller = MouseController()

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

while cap.isOpened():
    success, frame = cap.read()
    if not success: break
    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape
    
    c_time = time.time()
    fps = 1/(c_time-p_time) if (c_time-p_time) > 0 else 30
    p_time = c_time

    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
    result = detector.detect(mp_image)

    if result.hand_landmarks:
        hand = result.hand_landmarks[0]

        distance_val = spotify.get_hand_distance(hand, w, h)
        action_status = spotify.execute(hand)

        # Draw Skeleton lines FIRST (so they are under the dots)
        for connection in HAND_CONNECTIONS:
            start_idx = connection[0]
            end_idx = connection[1]
            p1 = (int(hand[start_idx].x * w), int(hand[start_idx].y * h))
            p2 = (int(hand[end_idx].x * w), int(hand[end_idx].y * h))
            cv2.line(frame, p1, p2, (255, 255, 255), 1) # White lines

        if action_status == "IDLE" or action_status == "COOLDOWN":
            my_controller.process(hand, False, distance_val, w, h)
        else:
            cv2.putText(frame, f"EXECUTED: {action_status}", (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        # Visual HUD - Joint Dots
        color = (0, 0, 255) if action_status != "IDLE" else (0, 255, 0)
        for lm in hand:
            cv2.circle(frame, (int(lm.x * w), int(lm.y * h)), 3, color, -1)
        
        # Highlight the Index Fingertip (The Mouse Cursor)
        cv2.circle(frame, (int(hand[8].x * w), int(hand[8].y * h)), 8, color, 2)

        # Draw the active "Sweet Spot" rectangle
        cv2.rectangle(frame, (int(w*ZONE_MARGIN), int(h*ZONE_MARGIN)),
                      (int(w*(1-ZONE_MARGIN)), int(h*(1-ZONE_MARGIN))), (255, 255, 255), 1)
    
    cv2.putText(frame, f"FPS: {int(fps)}", (10, 30), cv2.FONT_HERSHEY_PLAIN, 1, (255,0,0), 1)
    cv2.imshow('Gesture Engine', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()