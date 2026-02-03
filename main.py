"""
MAIN APPLICATION
Integrates gesture detection with media control actions
Implements state machine with cooldown logic
"""

import cv2
import time
import config
from gesture_engine import GestureEngine
from media_controller import create_controller


class GestureMediaController:
    """Main application class that coordinates gesture detection and media control"""
    
    def __init__(self):
        print("=" * 60)
        print("🎮 HOLOGRAPHIC GESTURE CONTROL SYSTEM")
        print("=" * 60)
        print()
        
        # Initialize components
        self.gesture_engine = GestureEngine()
        self.media_controller = create_controller()
        
        # State tracking
        self.last_action_time = 0
        self.last_action = None
        self.action_history = []
        
        # Volume tracking for pinch gestures
        self.volume_accumulator = 0
        self.last_pinch_time = 0
        
        # Performance tracking
        self.frame_times = []
        self.start_time = time.time()
        
        print()
        print("✅ System Ready!")
        print()
        self._print_controls()
    
    def _print_controls(self):
        """Print control instructions"""
        print("=" * 60)
        print("📋 GESTURE CONTROLS")
        print("=" * 60)
        print("✊ FIST              → Play/Pause Toggle")
        print("🤚➡️ SWIPE RIGHT      → Next Track")
        print("🤚⬅️ SWIPE LEFT       → Previous Track")
        print("🤏 PINCH OPEN       → Volume Up (spread thumb & index)")
        print("🤏 PINCH CLOSE      → Volume Down (bring thumb & index together)")
        print()
        print("⌨️ KEYBOARD CONTROLS")
        print("=" * 60)
        print("Q - Quit application")
        print("D - Toggle debug info")
        print("R - Reset cooldowns")
        print("S - Show statistics")
        print("=" * 60)
        print()
    
    def execute_action(self, gesture, gesture_data, current_time):
        """Execute media control action based on detected gesture"""
        # Check cooldown (except for volume which needs continuous control)
        if gesture not in ['pinch_open', 'pinch_close']:
            if (current_time - self.last_action_time) < config.GESTURE_COOLDOWN:
                if config.DEBUG_MODE:
                    print(f"⏳ Cooldown active: {config.GESTURE_COOLDOWN - (current_time - self.last_action_time):.2f}s remaining")
                return None
        
        action_result = None
        action_name = None
        
        # Map gestures to actions
        if gesture == "fist":
            self.media_controller.play_pause()
            action_name = "▶️⏸️ PLAY/PAUSE"
            action_result = True
            self.last_action_time = current_time
        
        elif gesture == "swipe_right":
            self.media_controller.next_track()
            action_name = "⏭️ NEXT TRACK"
            action_result = True
            self.last_action_time = current_time
        
        elif gesture == "swipe_left":
            self.media_controller.prev_track()
            action_name = "⏮️ PREVIOUS TRACK"
            action_result = True
            self.last_action_time = current_time
        
        elif gesture == "pinch_open":
            # Volume up - allow more frequent updates
            if (current_time - self.last_pinch_time) > 0.1:  # 100ms between volume updates
                volume_delta = gesture_data.get('volume_delta', 0)
                amount = int(abs(volume_delta) * config.PINCH_VOLUME_SENSITIVITY)
                amount = max(1, min(10, amount))  # Clamp between 1-10
                
                self.media_controller.volume_up(amount)
                action_name = f"🔊 VOLUME UP +{amount}%"
                action_result = True
                self.last_pinch_time = current_time
        
        elif gesture == "pinch_close":
            # Volume down - allow more frequent updates
            if (current_time - self.last_pinch_time) > 0.1:
                volume_delta = gesture_data.get('volume_delta', 0)
                amount = int(abs(volume_delta) * config.PINCH_VOLUME_SENSITIVITY)
                amount = max(1, min(10, amount))
                
                self.media_controller.volume_down(amount)
                action_name = f"🔉 VOLUME DOWN -{amount}%"
                action_result = True
                self.last_pinch_time = current_time
        
        # Log action
        if action_result and config.LOG_GESTURES:
            print(f"✅ {action_name}")
            self.action_history.append({
                'time': current_time,
                'gesture': gesture,
                'action': action_name
            })
            self.last_action = action_name
        
        return action_name
    
    def draw_action_feedback(self, frame, action_name, current_time):
        """Draw action feedback on frame"""
        if not config.SHOW_ACTION_FEEDBACK or not action_name:
            return frame
        
        h, w = frame.shape[:2]
        
        # Draw action name in large text at center
        text_size = cv2.getTextSize(action_name, cv2.FONT_HERSHEY_SIMPLEX, 1.5, 3)[0]
        text_x = (w - text_size[0]) // 2
        text_y = h - 100
        
        # Draw background rectangle
        padding = 20
        cv2.rectangle(frame, 
                     (text_x - padding, text_y - text_size[1] - padding),
                     (text_x + text_size[0] + padding, text_y + padding),
                     (0, 0, 0), -1)
        cv2.rectangle(frame, 
                     (text_x - padding, text_y - text_size[1] - padding),
                     (text_x + text_size[0] + padding, text_y + padding),
                     config.COLOR_ACTION, 3)
        
        # Draw text
        cv2.putText(frame, action_name, (text_x, text_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.5, config.COLOR_ACTION, 3)
        
        return frame
    
    def draw_cooldown_indicator(self, frame, current_time):
        """Draw cooldown timer visualization"""
        if not config.SHOW_COOLDOWN_TIMER:
            return frame
        
        h, w = frame.shape[:2]
        cooldown_remaining = config.GESTURE_COOLDOWN - (current_time - self.last_action_time)
        
        if cooldown_remaining > 0:
            # Draw progress bar
            bar_width = 300
            bar_height = 20
            bar_x = (w - bar_width) // 2
            bar_y = h - 50
            
            progress = 1.0 - (cooldown_remaining / config.GESTURE_COOLDOWN)
            fill_width = int(bar_width * progress)
            
            # Background
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height),
                         (50, 50, 50), -1)
            # Progress
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_width, bar_y + bar_height),
                         config.COLOR_COOLDOWN, -1)
            # Border
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height),
                         config.COLOR_TEXT, 2)
            
            # Text
            cv2.putText(frame, f"Cooldown: {cooldown_remaining:.1f}s", 
                       (bar_x, bar_y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, config.COLOR_TEXT, 2)
        
        return frame
    
    def draw_ui_overlay(self, frame):
        """Draw persistent UI overlay with instructions"""
        h, w = frame.shape[:2]
        
        # Semi-transparent background for instructions
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, h - 120), (400, h - 10), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        
        # Instructions
        instructions = [
            "✊ Fist = Play/Pause",
            "🤚↔️ Swipe = Prev/Next",
            "🤏 Pinch = Volume",
            "Q = Quit | S = Stats"
        ]
        
        y_offset = h - 100
        for instruction in instructions:
            cv2.putText(frame, instruction, (20, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, config.COLOR_TEXT, 1)
            y_offset += 25
        
        return frame
    
    def show_statistics(self):
        """Print performance statistics"""
        print("\n" + "=" * 60)
        print("📊 PERFORMANCE STATISTICS")
        print("=" * 60)
        
        runtime = time.time() - self.start_time
        print(f"Runtime: {runtime:.1f}s")
        
        if self.frame_times:
            avg_fps = len(self.frame_times) / runtime
            print(f"Average FPS: {avg_fps:.1f}")
        
        print(f"\nTotal Actions Executed: {len(self.action_history)}")
        
        if self.action_history:
            print("\nRecent Actions:")
            for action in self.action_history[-10:]:
                print(f"  {action['action']} at {action['time'] - self.start_time:.1f}s")
        
        controller_status = self.media_controller.get_status()
        print(f"\nController: {controller_status.get('controller', 'unknown')}")
        print(f"Volume: {controller_status.get('volume', 'N/A')}%")
        
        print("=" * 60 + "\n")
    
    def run(self):
        """Main application loop"""
        cap = cv2.VideoCapture(config.CAMERA_INDEX)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
        cap.set(cv2.CAP_PROP_FPS, config.CAMERA_FPS)
        
        print("🎥 Camera started. Show your right hand to begin!")
        print()
        
        current_action_name = None
        action_display_time = 0
        
        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    print("❌ Failed to capture frame")
                    break
                
                current_time = time.time()
                self.frame_times.append(current_time)
                
                # Flip frame for mirror effect
                frame = cv2.flip(frame, 1)
                
                # Process frame with gesture engine
                frame, confirmed_gesture, gesture_data = self.gesture_engine.process_frame(frame)
                
                # Execute action if gesture confirmed
                if confirmed_gesture and confirmed_gesture != "none":
                    action_name = self.execute_action(confirmed_gesture, gesture_data, current_time)
                    if action_name:
                        current_action_name = action_name
                        action_display_time = current_time
                
                # Draw action feedback (fade out after 2 seconds)
                if current_action_name and (current_time - action_display_time) < 2.0:
                    frame = self.draw_action_feedback(frame, current_action_name, current_time)
                
                # Draw cooldown indicator
                frame = self.draw_cooldown_indicator(frame, current_time)
                
                # Draw UI overlay
                frame = self.draw_ui_overlay(frame)
                
                # Show frame
                cv2.imshow('Holographic Gesture Control', frame)
                
                # Handle keyboard input
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("\n👋 Shutting down...")
                    break
                elif key == ord('s'):
                    self.show_statistics()
                elif key == ord('r'):
                    self.last_action_time = 0
                    print("🔄 Cooldowns reset")
                elif key == ord('d'):
                    config.DEBUG_MODE = not config.DEBUG_MODE
                    print(f"🐛 Debug mode: {'ON' if config.DEBUG_MODE else 'OFF'}")
        
        except KeyboardInterrupt:
            print("\n⚠️ Interrupted by user")
        
        finally:
            # Cleanup
            print("🧹 Cleaning up...")
            cap.release()
            cv2.destroyAllWindows()
            self.gesture_engine.cleanup()
            
            # Final statistics
            self.show_statistics()
            
            print("✅ Goodbye!")


if __name__ == "__main__":
    app = GestureMediaController()
    app.run()