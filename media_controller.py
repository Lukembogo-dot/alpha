import platform
import time
import config

class SystemMediaController:
    def __init__(self):
        self.os_type = platform.system()
        self.use_pycaw = False
        self.last_call = 0
        
        if self.os_type == "Windows":
            try:
                import pythoncom
                pythoncom.CoInitialize()
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                from comtypes import CLSCTX_ALL
                
                devices = AudioUtilities.GetSpeakers()
                # FIXED: The correct way to activate the volume interface
                self.interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                self.volume_control = self.interface.QueryInterface(IAudioEndpointVolume)
                self.use_pycaw = True
                print("✅ Windows Audio Engine Restored")
            except Exception as e:
                print(f"⚠️ Audio Init Error: {e}")

    def volume_up(self, amount=5):
        if time.time() - self.last_call < 0.1: return
        self.last_call = time.time()
        if self.use_pycaw:
            curr = self.volume_control.GetMasterVolumeLevelScalar()
            self.volume_control.SetMasterVolumeLevelScalar(min(1.0, curr + 0.05), None)
        else:
            import pyautogui
            pyautogui.press('volumeup')

    def volume_down(self, amount=5):
        if time.time() - self.last_call < 0.1: return
        self.last_call = time.time()
        if self.use_pycaw:
            curr = self.volume_control.GetMasterVolumeLevelScalar()
            self.volume_control.SetMasterVolumeLevelScalar(max(0.0, curr - 0.05), None)
        else:
            import pyautogui
            pyautogui.press('volumedown')

    def play_pause(self):
        import pyautogui
        pyautogui.press('playpause')
        return True

    def next_track(self):
        try:
            import pyautogui
            # Double press for instant skip response
            pyautogui.press('nexttrack')
            time.sleep(0.1)  # Tiny delay
            pyautogui.press('nexttrack')
            print("⏭️⏭️ Executed: Double Next (Skip Track)")
            return True
        except Exception as e:
            print(f"❌ Next Error: {e}")
            return False

    def prev_track(self):
        try:
            import pyautogui
            # Send TWO presses to ensure it skips the song, not just restarts it
            pyautogui.press('prevtrack')
            time.sleep(0.1)  # Tiny delay
            pyautogui.press('prevtrack')
            print("⏮️⏮️ Executed: Double Previous (Skip Track)")
            return True
        except Exception as e:
            print(f"❌ Previous Error: {e}")
            return False

    def get_status(self):
        return {'controller': 'system'}

def create_controller():
    return SystemMediaController()
