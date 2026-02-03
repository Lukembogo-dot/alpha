"""
MEDIA CONTROLLER - Action Layer
Handles system-wide media controls with future support for Spotify/YouTube APIs
"""

import platform
import subprocess
import time
from abc import ABC, abstractmethod
import config


class MediaController(ABC):
    """Abstract base class for media controllers"""
    
    @abstractmethod
    def play_pause(self):
        """Toggle play/pause"""
        pass
    
    @abstractmethod
    def next_track(self):
        """Skip to next track"""
        pass
    
    @abstractmethod
    def prev_track(self):
        """Go to previous track"""
        pass
    
    @abstractmethod
    def volume_up(self, amount=5):
        """Increase volume by percentage"""
        pass
    
    @abstractmethod
    def volume_down(self, amount=5):
        """Decrease volume by percentage"""
        pass
    
    @abstractmethod
    def get_status(self):
        """Get current playback status"""
        pass


class SystemMediaController(MediaController):
    """
    System-wide media controller using OS native media keys.
    Works with ANY application: Spotify, YouTube, Apple Music, VLC, etc.
    """
    
    def __init__(self):
        self.os_type = platform.system()
        print(f"🎵 System Media Controller initialized for {self.os_type}")
        
        # Try to import appropriate library for the OS
        if self.os_type == "Windows":
            try:
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                from comtypes import CLSCTX_ALL
                self.audio_available = True
                
                # Get the default audio device
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                self.volume_control = interface.QueryInterface(IAudioEndpointVolume)
                print("✅ Windows audio control initialized")
            except Exception as e:
                print(f"⚠️ Windows audio control not available: {e}")
                print("   Install with: pip install pycaw comtypes")
                self.audio_available = False
        
        elif self.os_type == "Darwin":  # macOS
            self.audio_available = True
            print("✅ macOS audio control initialized")
        
        elif self.os_type == "Linux":
            self.audio_available = True
            print("✅ Linux audio control initialized")
        
        self.current_volume = 50  # Track volume level (0-100)
    
    def _send_media_key_windows(self, key_code):
        """Send media key on Windows"""
        try:
            # Use nircmd if available, otherwise try pyautogui
            try:
                import pyautogui
                key_map = {
                    'play_pause': 'playpause',
                    'next': 'nexttrack',
                    'prev': 'prevtrack',
                }
                if key_code in key_map:
                    pyautogui.press(key_map[key_code])
                    return True
            except ImportError:
                print("⚠️ Install pyautogui for better media control: pip install pyautogui")
                return False
        except Exception as e:
            print(f"Error sending media key: {e}")
            return False
    
    def _send_media_key_macos(self, key_code):
        """Send media key on macOS using AppleScript"""
        try:
            scripts = {
                'play_pause': 'tell application "System Events" to keystroke " " using {option down}',
                'next': 'tell application "System Events" to keystroke "l" using {option down, command down}',
                'prev': 'tell application "System Events" to keystroke "j" using {option down, command down}',
            }
            
            if key_code in scripts:
                subprocess.run(['osascript', '-e', scripts[key_code]], 
                             capture_output=True, check=True)
                return True
        except Exception as e:
            print(f"Error sending media key: {e}")
            return False
    
    def _send_media_key_linux(self, key_code):
        """Send media key on Linux using playerctl"""
        try:
            commands = {
                'play_pause': 'play-pause',
                'next': 'next',
                'prev': 'previous',
            }
            
            if key_code in commands:
                subprocess.run(['playerctl', commands[key_code]], 
                             capture_output=True, check=True)
                return True
        except FileNotFoundError:
            print("⚠️ Install playerctl for media control: sudo apt-get install playerctl")
            return False
        except Exception as e:
            print(f"Error sending media key: {e}")
            return False
    
    def play_pause(self):
        """Toggle play/pause"""
        if self.os_type == "Windows":
            return self._send_media_key_windows('play_pause')
        elif self.os_type == "Darwin":
            return self._send_media_key_macos('play_pause')
        elif self.os_type == "Linux":
            return self._send_media_key_linux('play_pause')
        return False
    
    def next_track(self):
        """Skip to next track"""
        if self.os_type == "Windows":
            return self._send_media_key_windows('next')
        elif self.os_type == "Darwin":
            return self._send_media_key_macos('next')
        elif self.os_type == "Linux":
            return self._send_media_key_linux('next')
        return False
    
    def prev_track(self):
        """Go to previous track"""
        if self.os_type == "Windows":
            return self._send_media_key_windows('prev')
        elif self.os_type == "Darwin":
            return self._send_media_key_macos('prev')
        elif self.os_type == "Linux":
            return self._send_media_key_linux('prev')
        return False
    
    def volume_up(self, amount=5):
        """Increase volume"""
        if not self.audio_available:
            return False
        
        try:
            if self.os_type == "Windows":
                # Get current volume
                current = self.volume_control.GetMasterVolumeLevelScalar()
                # Increase by amount (convert to 0.0-1.0 scale)
                new_volume = min(1.0, current + (amount / 100.0))
                self.volume_control.SetMasterVolumeLevelScalar(new_volume, None)
                self.current_volume = int(new_volume * 100)
                return True
            
            elif self.os_type == "Darwin":
                # macOS volume control
                current = int(subprocess.check_output(
                    ['osascript', '-e', 'output volume of (get volume settings)']
                ).decode().strip())
                new_volume = min(100, current + amount)
                subprocess.run(['osascript', '-e', f'set volume output volume {new_volume}'])
                self.current_volume = new_volume
                return True
            
            elif self.os_type == "Linux":
                # Linux volume control using amixer
                subprocess.run(['amixer', '-D', 'pulse', 'sset', 'Master', f'{amount}%+'],
                             capture_output=True)
                return True
        
        except Exception as e:
            print(f"Error adjusting volume: {e}")
            return False
    
    def volume_down(self, amount=5):
        """Decrease volume"""
        if not self.audio_available:
            return False
        
        try:
            if self.os_type == "Windows":
                current = self.volume_control.GetMasterVolumeLevelScalar()
                new_volume = max(0.0, current - (amount / 100.0))
                self.volume_control.SetMasterVolumeLevelScalar(new_volume, None)
                self.current_volume = int(new_volume * 100)
                return True
            
            elif self.os_type == "Darwin":
                current = int(subprocess.check_output(
                    ['osascript', '-e', 'output volume of (get volume settings)']
                ).decode().strip())
                new_volume = max(0, current - amount)
                subprocess.run(['osascript', '-e', f'set volume output volume {new_volume}'])
                self.current_volume = new_volume
                return True
            
            elif self.os_type == "Linux":
                subprocess.run(['amixer', '-D', 'pulse', 'sset', 'Master', f'{amount}%-'],
                             capture_output=True)
                return True
        
        except Exception as e:
            print(f"Error adjusting volume: {e}")
            return False
    
    def get_status(self):
        """Get current playback status"""
        return {
            'volume': self.current_volume,
            'controller': 'system',
            'available': True
        }


class SpotifyController(MediaController):
    """
    Spotify API controller - ready for when Spotify API is available
    This is a placeholder that you can fill in with actual Spotify API calls
    """
    
    def __init__(self):
        print("🎵 Spotify Controller (Placeholder - API under maintenance)")
        print("   Add your credentials to config.py when API is available")
        self.authenticated = False
        
        # TODO: Add Spotify authentication when API is available
        # self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(...))
    
    def play_pause(self):
        print("▶️⏸️ Spotify Play/Pause (API not available yet)")
        return False
    
    def next_track(self):
        print("⏭️ Spotify Next Track (API not available yet)")
        return False
    
    def prev_track(self):
        print("⏮️ Spotify Previous Track (API not available yet)")
        return False
    
    def volume_up(self, amount=5):
        print(f"🔊 Spotify Volume Up {amount}% (API not available yet)")
        return False
    
    def volume_down(self, amount=5):
        print(f"🔉 Spotify Volume Down {amount}% (API not available yet)")
        return False
    
    def get_status(self):
        return {
            'authenticated': self.authenticated,
            'controller': 'spotify',
            'available': False
        }


class YouTubeController(MediaController):
    """
    YouTube Music controller - placeholder for future implementation
    """
    
    def __init__(self):
        print("🎵 YouTube Music Controller (Not implemented yet)")
    
    def play_pause(self):
        return False
    
    def next_track(self):
        return False
    
    def prev_track(self):
        return False
    
    def volume_up(self, amount=5):
        return False
    
    def volume_down(self, amount=5):
        return False
    
    def get_status(self):
        return {'controller': 'youtube', 'available': False}


# Factory function to create the appropriate controller
def create_controller():
    """Create and return the appropriate media controller based on config"""
    controller_type = config.ACTIVE_CONTROLLER.lower()
    
    if controller_type == "system":
        return SystemMediaController()
    elif controller_type == "spotify":
        return SpotifyController()
    elif controller_type == "youtube":
        return YouTubeController()
    else:
        print(f"⚠️ Unknown controller type: {controller_type}, defaulting to system")
        return SystemMediaController()


if __name__ == "__main__":
    # Test the controller
    print("Testing Media Controller...")
    controller = create_controller()
    
    print("\nController Status:")
    print(controller.get_status())
    
    print("\nTest commands (press Enter to test each):")
    input("Press Enter to test Play/Pause...")
    controller.play_pause()
    
    input("Press Enter to test Next Track...")
    controller.next_track()
    
    input("Press Enter to test Volume Up...")
    controller.volume_up(10)
    
    print("\n✅ Test complete!")