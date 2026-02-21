# app/audio/player.py
"""Audio playback via ffplay with queue support."""
from __future__ import annotations
import subprocess
import threading
import queue
from typing import Optional
from dataclasses import dataclass

@dataclass
class PlaybackRequest:
    """Represents a playback request in the queue."""
    data: bytes
    ffplay_bin: str
    volume: float
    skip_event: Optional[threading.Event] = None


class AudioPlayer:
    """
    Singleton audio player with queued playback.
    
    Ensures audio clips play sequentially without overlapping.
    Supports skipping the current playback.
    """
    _instance: Optional["AudioPlayer"] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> "AudioPlayer":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self) -> None:
        if self._initialized:
            return
        self._queue: queue.Queue[Optional[PlaybackRequest]] = queue.Queue()
        self._worker_thread: Optional[threading.Thread] = None
        self._current_proc: Optional[subprocess.Popen] = None
        self._stop_event = threading.Event()
        self._skip_event = threading.Event()
        self._lock = threading.Lock()
        self._initialized = True
        self._start_worker()
    
    def _start_worker(self) -> None:
        """Start the background worker thread that processes the queue."""
        self._worker_thread = threading.Thread(target=self._worker, daemon=True, name="audio-player-worker")
        self._worker_thread.start()
    
    def _worker(self) -> None:
        """Worker loop: process playback requests sequentially."""
        while not self._stop_event.is_set():
            try:
                req = self._queue.get(timeout=0.5)
                if req is None:  # Shutdown signal
                    break
                self._play_blocking(req)
                self._queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[player] Worker error: {e}")
    
    def _play_blocking(self, req: PlaybackRequest) -> None:
        """
        Play audio synchronously (blocks worker thread until done or skipped).
        
        Args:
            req: Playback request with audio data and settings
        """
        proc = None
        try:
            volume_int = int(req.volume * 256)
            cmd = [
                req.ffplay_bin,
                "-hide_banner",
                "-loglevel", "quiet",
                "-nodisp",
                "-autoexit",
                "-volume", str(volume_int),
                "-i", "pipe:0",
            ]
            with self._lock:
                proc = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                self._current_proc = proc
            
            # Write audio data to stdin
            proc.stdin.write(req.data)
            proc.stdin.close()
            
            # Wait for completion or skip signal
            while proc.poll() is None:
                if self._skip_event.is_set():
                    self._skip_event.clear()
                    proc.terminate()
                    try:
                        proc.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                    print("[player] Playback skipped")
                    return
                try:
                    proc.wait(timeout=0.3)
                except subprocess.TimeoutExpired:
                    continue
                    
        except FileNotFoundError:
            print(f"[player] Warning: ffplay not found at '{req.ffplay_bin}'. "
                  "Install ffmpeg package (includes ffplay).")
        except Exception as e:
            print(f"[player] Error during playback: {e}")
        finally:
            with self._lock:
                if self._current_proc is proc:
                    self._current_proc = None
    
    def play(self, data: bytes, ffplay_bin: str = "ffplay", volume: float = 1.0) -> None:
        """
        Queue audio for playback.
        
        Args:
            data: Audio bytes (WAV, MP3, etc.)
            ffplay_bin: Path to ffplay executable
            volume: Volume (0.0-10.0, 1.0 = 100%)
        """
        req = PlaybackRequest(data=data, ffplay_bin=ffplay_bin, volume=volume)
        self._queue.put(req)
    
    def skip(self) -> bool:
        """
        Skip the currently playing audio.
        
        Returns:
            True if skip was initiated, False if nothing was playing
        """
        with self._lock:
            if self._current_proc is not None and self._current_proc.poll() is None:
                self._skip_event.set()
                return True
        return False
    
    def stop(self) -> None:
        """Stop the player and shutdown the worker thread."""
        self._stop_event.set()
        self._queue.put(None)  # Signal worker to exit
        if self._worker_thread is not None:
            self._worker_thread.join(timeout=2)
        with self._lock:
            if self._current_proc is not None:
                self._current_proc.terminate()


# Global singleton instance
_player: Optional[AudioPlayer] = None
_player_lock = threading.Lock()


def _get_player() -> AudioPlayer:
    """Get or create the singleton AudioPlayer instance."""
    global _player
    with _player_lock:
        if _player is None:
            _player = AudioPlayer()
        return _player


def play_audio(data: bytes, ffplay_bin: str = "ffplay", volume: float = 1.0) -> None:
    """
    Queue audio for playback (non-blocking).
    
    Audio will be played sequentially with other queued items.
    
    Args:
        data: Audio bytes (WAV, MP3, etc.)
        ffplay_bin: Path to ffplay executable
        volume: Volume (0.0-10.0, 1.0 = 100%)
    """
    _get_player().play(data, ffplay_bin, volume)


def skip_playback() -> bool:
    """
    Skip the currently playing audio.
    
    Returns:
        True if skip was initiated, False if nothing was playing
    """
    return _get_player().skip()


def stop_player() -> None:
    """Stop the player and shutdown the worker thread."""
    global _player
    with _player_lock:
        if _player is not None:
            _player.stop()
            _player = None
