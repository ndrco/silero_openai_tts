# app/audio/player.py
"""Audio playback via ffplay."""
from __future__ import annotations
import subprocess
import threading
from typing import Optional

def play_audio(data: bytes, ffplay_bin: str = "ffplay", volume: float = 1.0) -> None:
    """
    Plays audio via ffplay in a background thread.

    Args:
        data: Audio bytes (WAV, MP3, etc.)
        ffplay_bin: Path to ffplay executable
        volume: Volume (0.0-10.0, 1.0 = 100%)
    """
    def _play():
        try:
            # Use WAV for better quality (no re-encoding)
            # -nodisp: disable video window
            # -autoexit: exit after playback ends
            # -volume: volume (0-65535, 256 = 100%)
            volume_int = int(volume * 256)
            cmd = [
                ffplay_bin,
                "-hide_banner",
                "-loglevel", "quiet",
                "-nodisp",
                "-autoexit",
                "-volume", str(volume_int),
                "-i", "pipe:0",
            ]
            proc = subprocess.run(
                cmd,
                input=data,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            print(f"[player] Warning: ffplay not found at '{ffplay_bin}'. "
                  "Install ffmpeg package (includes ffplay).")
        except Exception as e:
            print(f"[player] Error during playback: {e}")

    # Run in a separate thread to avoid blocking the client response
    thread = threading.Thread(target=_play, daemon=True)
    thread.start()
