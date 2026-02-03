# ========================================
# GESTURE CONTROL SYSTEM - CONFIGURATION
# ========================================

# === ACTIVE CONTROLLER ===
# Options: "system", "spotify", "youtube"
ACTIVE_CONTROLLER = "system"  # Using system-wide media controls for now

# === GESTURE SENSITIVITY SETTINGS ===
# Swipe Detection
SWIPE_THRESHOLD_CM = 15  # Moderate: 15cm movement triggers swipe
SWIPE_MIN_VELOCITY = 0.3  # Minimum velocity to count as intentional swipe

# Pinch Detection (for volume control)
PINCH_DEADZONE_CM = 2  # Ignore movements smaller than 2cm
PINCH_MIN_DISTANCE = 2  # Minimum distance between thumb and index (cm)
PINCH_MAX_DISTANCE = 15  # Maximum distance for pinch detection (cm)
PINCH_VOLUME_SENSITIVITY = 3  # Volume change per cm of pinch movement

# Fist Detection
FIST_CONFIDENCE_THRESHOLD = 0.8  # How confident we need to be it's a fist

# === TIMING & COOLDOWN ===
GESTURE_COOLDOWN = 0.8  # Balanced: 0.8s between gesture commands
GESTURE_HOLD_TIME = 0.25  # Gesture must be held for 0.25s to trigger
STATE_TRANSITION_DELAY = 0.15  # Delay before state transitions

# === ANTI-JITTER SETTINGS ===
# Smoothing
LANDMARK_BUFFER_SIZE = 7  # Number of frames to average (higher = smoother but more lag)
POSITION_SMOOTHING_FACTOR = 0.3  # Lower = more smoothing (0.1-0.5 recommended)

# Jitter Reduction
JITTER_THRESHOLD_PX = 2  # Target: <2 pixel variance when hand is still
MIN_MOVEMENT_THRESHOLD = 0.005  # Ignore movements smaller than this (normalized coords)

# === DEPTH COMPENSATION ===
# Z-axis normalization for perspective-invariant interaction
MIN_DEPTH_CM = 10  # Minimum hand distance from camera
MAX_DEPTH_CM = 60  # Maximum hand distance from camera
DEPTH_SCALE_FACTOR = 1.5  # Multiplier for depth-based scaling

# === CAMERA SETTINGS ===
CAMERA_INDEX = 0  # Default webcam
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720
CAMERA_FPS = 60  # Request 60fps (actual may vary)

# === MEDIAPIPE SETTINGS ===
MP_MIN_DETECTION_CONFIDENCE = 0.7  # Higher = less false positives
MP_MIN_TRACKING_CONFIDENCE = 0.7  # Higher = smoother tracking
MP_MODEL_COMPLEXITY = 1  # 0=lite, 1=full (more accurate)
MP_MAX_HANDS = 1  # Track only right hand

# === VISUAL FEEDBACK ===
SHOW_SKELETON = True  # Show hand skeleton tracking
SHOW_METRICS = True  # Show FPS, jitter, depth metrics
SHOW_GESTURE_NAME = True  # Show current gesture name
SHOW_ACTION_FEEDBACK = True  # Show action confirmations (▶️ PLAY, etc.)
SHOW_COOLDOWN_TIMER = True  # Show cooldown visualization
SHOW_VOLUME_BAR = True  # Show volume level indicator

# UI Colors (BGR format)
COLOR_SKELETON = (0, 255, 0)  # Green
COLOR_JOINTS = (0, 0, 255)  # Red
COLOR_FINGERTIPS = (255, 0, 0)  # Blue
COLOR_TEXT = (255, 255, 255)  # White
COLOR_ACTION = (0, 255, 255)  # Yellow
COLOR_COOLDOWN = (0, 165, 255)  # Orange

# === SPOTIFY API SETTINGS (for future use) ===
SPOTIFY_CLIENT_ID = ""  # Add your client ID when available
SPOTIFY_CLIENT_SECRET = ""  # Add your client secret when available
SPOTIFY_REDIRECT_URI = "http://localhost:8888/callback"

# === GESTURE MAPPING ===
# Define which gestures trigger which actions
GESTURE_ACTIONS = {
    "fist": "play_pause",
    "swipe_right": "next_track",
    "swipe_left": "prev_track",
    "pinch_open": "volume_up",
    "pinch_close": "volume_down",
    "pointing": "cursor_mode",  # Reserved for future
}

# === DEBUG MODE ===
DEBUG_MODE = True  # Print debug info to console
LOG_GESTURES = True  # Log all detected gestures
SAVE_METRICS = False  # Save performance metrics to file