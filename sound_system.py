"""
Sound System for Tradegame
Handles all sound effects and background music
"""

import pygame
import os
from config import get_path, logging

class SoundSystem:
    def __init__(self):
        """Initialize the sound system."""
        self.enabled = True
        self.sfx_enabled = True  # Alias for compatibility
        self.music_enabled = True
        self.sfx_volume = 0.7
        self.music_volume = 0.3
        self.sounds = {}
        self.sounds_dir = get_path("sounds")

        # Initialize pygame mixer
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self._load_sounds()
            logging.info("Sound-System initialisiert")
        except Exception as e:
            logging.error(f"Fehler beim Initialisieren des Sound-Systems: {e}")
            self.enabled = False

    def _load_sounds(self):
        """Load all sound effects."""
        sound_files = {
            "buy": "buy.wav",
            "sell": "sell.wav",
            "card_draw": "card_draw.wav",
            "chat": "chat.wav",
            "win": "win.wav",
            "lose": "lose.wav",
            "crash": "crash.wav",
            "bonus": "bonus.wav",
            "click": "click.wav",
            "error": "error.wav",
            "round_start": "round_start.wav",
            "crypto_unlock": "crypto_unlock.wav"
        }

        for name, filename in sound_files.items():
            path = os.path.join(self.sounds_dir, filename)
            if os.path.exists(path):
                try:
                    self.sounds[name] = pygame.mixer.Sound(path)
                    self.sounds[name].set_volume(self.sfx_volume)
                except Exception as e:
                    logging.warning(f"Konnte Sound {filename} nicht laden: {e}")

    def play(self, sound_name):
        """Play a sound effect."""
        if not self.enabled:
            return

        if sound_name in self.sounds:
            try:
                self.sounds[sound_name].play()
            except Exception as e:
                logging.error(f"Fehler beim Abspielen von {sound_name}: {e}")

    def play_music(self, filename="background_music.mp3", loop=True):
        """Play background music."""
        if not self.music_enabled:
            return

        path = os.path.join(self.sounds_dir, filename)
        if os.path.exists(path):
            try:
                pygame.mixer.music.load(path)
                pygame.mixer.music.set_volume(self.music_volume)
                pygame.mixer.music.play(-1 if loop else 0)
                logging.info(f"Musik gestartet: {filename}")
            except Exception as e:
                logging.error(f"Fehler beim Abspielen der Musik: {e}")

    def stop_music(self):
        """Stop background music."""
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass

    def pause_music(self):
        """Pause background music."""
        try:
            pygame.mixer.music.pause()
        except Exception:
            pass

    def resume_music(self):
        """Resume background music."""
        try:
            pygame.mixer.music.unpause()
        except Exception:
            pass

    def set_sfx_volume(self, volume):
        """Set sound effects volume (0.0 - 1.0)."""
        self.sfx_volume = max(0.0, min(1.0, volume))
        for sound in self.sounds.values():
            sound.set_volume(self.sfx_volume)

    def set_music_volume(self, volume):
        """Set music volume (0.0 - 1.0)."""
        self.music_volume = max(0.0, min(1.0, volume))
        try:
            pygame.mixer.music.set_volume(self.music_volume)
        except Exception:
            pass

    def toggle_sfx(self):
        """Toggle sound effects on/off."""
        self.enabled = not self.enabled
        self.sfx_enabled = self.enabled  # Keep in sync
        return self.enabled

    def toggle_music(self):
        """Toggle music on/off."""
        self.music_enabled = not self.music_enabled
        if not self.music_enabled:
            self.stop_music()
        return self.music_enabled

# Global sound system instance
sound_system = SoundSystem()
