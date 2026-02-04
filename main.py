"""
MAIN APPLICATION (TWO-HANDED EDITION)
Integrates two-handed gesture detection with media control actions.
"""

import cv2
import time
import config
from gesture_engine import GestureEngine
from media_controller import create_controller

class GestureMediaController:
    def __init__(self):
        print("=" * 60)
        print("🎮 HOLOGRAPHIC GESTURE CONTROL - TWO-HANDED MODE")
        print("=" * 60)
        
        # Initialize components
        self.gesture_engine = GestureEngine()
        self.media_controller = create_controller()
        
        # UI State
        self.current_action = None
        self.action_time = 0
        
        print("\n✅ System Ready!")
        print("🤏 Pinch then move hand UP/DOWN to adjust volume.")
        print("✌️ Right Peace sign Wave = NEXT")
        print("✌️ Left Peace sign Wave  = PREVIOUS")
        print("✊ Fist (1.5s)     = PLAY/PAUSE")

    def run(self):
        cap = cv2.VideoCapture(config.CAMERA_INDEX)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
        
        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Mirror for natural interaction
                frame = cv2.flip(frame, 1)
                current_time = time.time()
                
                # Process frame (Now supports 2 hands)
                frame, gesture, data = self.gesture_engine.process_frame(frame)
                
                # Execute Actions based on the new logic
                if gesture != "none":
                    if gesture == "fist":
                        if self.media_controller.play_pause():
                            self.current_action = "▶️⏸️ PLAY/PAUSE"
                            self.action_time = current_time
                            
                    elif gesture == "swipe_right":
                        if self.media_controller.next_track():
                            self.current_action = "⏭️ NEXT TRACK (Right Hand)"
                            self.action_time = current_time
                            
                    elif gesture == "swipe_left":
                        if self.media_controller.prev_track():
                            self.current_action = "⏮️ PREVIOUS TRACK (Left Hand)"
                            self.action_time = current_time
                            
                    elif gesture == "pinch_open":
                        self.media_controller.volume_up()
                        self.current_action = "🔊 VOLUME UP"
                        self.action_time = current_time
                        
                    elif gesture == "pinch_close":
                        self.media_controller.volume_down()
                        self.current_action = "🔉 VOLUME DOWN"
                        self.action_time = current_time

                # Draw UI Feedback
                if self.current_action and (current_time - self.action_time < 2.0):
                    # Draw a nice background box for the action text
                    cv2.rectangle(frame, (10, 10), (450, 60), (0, 0, 0), -1)
                    cv2.putText(frame, self.current_action, (20, 45),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                
                cv2.imshow('Holographic Control', frame)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            cap.release()
            cv2.destroyAllWindows()
            self.gesture_engine.cleanup()

if __name__ == "__main__":
    app = GestureMediaController()
    app.run()
