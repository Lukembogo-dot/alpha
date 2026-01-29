import pyautogui
import time
import math

class OneEuroFilter:
    def __init__(self, freq, mincutoff=1.0, beta=0.0, dcutoff=1.0):
        self.freq = freq
        self.mincutoff = mincutoff
        self.beta = beta
        self.dcutoff = dcutoff
        self.x_prev = None
        self.dx_prev = None
        self.t_prev = None

    def __call__(self, x, t=None):
        if t is None:
            t = time.time()
        if self.x_prev is None:
            self.x_prev = x
            self.dx_prev = 0.0
            self.t_prev = t
            return x
        dt = t - self.t_prev
        dx = (x - self.x_prev) / dt
        edx = self.dx_prev + self.alpha(dt, self.dcutoff) * (dx - self.dx_prev)
        cutoff = self.mincutoff + self.beta * abs(edx)
        x_filtered = self.x_prev + self.alpha(dt, cutoff) * (x - self.x_prev)
        self.x_prev = x_filtered
        self.dx_prev = edx
        self.t_prev = t
        return x_filtered

    def alpha(self, dt, cutoff):
        tau = 1.0 / (2 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

class MouseController:
    def __init__(self):
        self.SCREEN_WIDTH, self.SCREEN_HEIGHT = pyautogui.size()
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0
        self.ZONE_MARGIN = 0.2
        self.prev_x, self.prev_y = 0, 0
        self.base_d = 150
        self.deadzone_px = 7
        self.filter_x = OneEuroFilter(30, 0.1, 0.1)
        self.filter_y = OneEuroFilter(30, 0.1, 0.1)

    def process(self, hand, is_fist, d, w, h):
        # Assumes is_fist is False
        dynamic_margin = self.ZONE_MARGIN * (self.base_d / d) if d > 0 else self.ZONE_MARGIN
        dynamic_margin = max(0.05, min(0.4, dynamic_margin))
        norm_x = (hand[8].x - dynamic_margin) / (1 - 2 * dynamic_margin)
        norm_y = (hand[8].y - dynamic_margin) / (1 - 2 * dynamic_margin)
        raw_x = norm_x * self.SCREEN_WIDTH
        raw_y = norm_y * self.SCREEN_HEIGHT
        raw_x = max(0, min(self.SCREEN_WIDTH, raw_x))
        raw_y = max(0, min(self.SCREEN_HEIGHT, raw_y))
        curr_x = self.filter_x(raw_x)
        curr_y = self.filter_y(raw_y)
        distance = math.sqrt((curr_x - self.prev_x)**2 + (curr_y - self.prev_y)**2)
        if distance > self.deadzone_px:
            pyautogui.moveTo(int(curr_x), int(curr_y), duration=0)
            self.prev_x, self.prev_y = curr_x, curr_y

class SpotifyController:
    def __init__(self):
        self.last_action_time = 0
        self.cooldown = 0.8  # Prevent rapid-fire triggering
        
    def get_hand_distance(self, hand, w, h):
        """Calculates distance between wrist (0) and middle finger knuckle (9) in pixels."""
        p0 = hand[0]
        p9 = hand[9]
        return math.sqrt((p9.x * w - p0.x * w)**2 + (p9.y * h - p0.y * h)**2)

    def detect_gesture(self, hand):
        """
        Interprets hand landmarks into specific Spotify actions.
        """
        # 1. Finger States (Is extended?)
        # Landmark 8=Index, 12=Middle, 16=Ring, 20=Pinky
        index_up = hand[8].y < hand[6].y
        middle_up = hand[12].y < hand[10].y
        ring_up = hand[16].y < hand[14].y
        pinky_up = hand[20].y < hand[18].y
        thumb_up = hand[4].x < hand[3].x # For mirrored right hand

        # 2. Gesture Logic
        # FIST: All fingers down
        if not (index_up or middle_up or ring_up or pinky_up):
            return "PLAY_PAUSE"
            
        # PEACE SIGN: Only Index and Middle up
        if index_up and middle_up and not (ring_up or pinky_up):
            return "NEXT_TRACK"

        # OK SIGN / PINCH: Thumb and Index close together (for future volume?)
        # For now, let's stick to simple clear gestures
        return "IDLE"

    def execute(self, hand):
        """Processes the gesture and hits the media keys."""
        gesture = self.detect_gesture(hand)
        current_time = time.time()

        # Cooldown check
        if current_time - self.last_action_time < self.cooldown:
            return "COOLDOWN"

        if gesture == "PLAY_PAUSE":
            pyautogui.press('playpause') # System-wide media key
            print("Action: Spotify Play/Pause")
            self.last_action_time = current_time
            return gesture

        elif gesture == "NEXT_TRACK":
            pyautogui.press('nexttrack') # System-wide media key
            print("Action: Spotify Next Track")
            self.last_action_time = current_time
            return gesture
            
        return "IDLE"