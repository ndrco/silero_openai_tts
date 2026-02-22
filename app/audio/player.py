# app/audio/player.py
"""Audio playback via ffplay with queue support."""
from __future__ import annotations

import queue
import subprocess
import threading
from dataclasses import dataclass
from typing import Optional


class _NoopSkipWindowController:
    """Fallback skip window controller when Tkinter UI is unavailable."""

    def on_playback_start(self) -> None:
        return

    def on_playback_finish(self) -> None:
        return

    def stop(self) -> None:
        return


class _TkSkipWindowController:
    """Tkinter-based window with a single "Skip" button."""

    def __init__(self, skip_callback) -> None:
        self._skip_callback = skip_callback
        self._events: queue.Queue[str] = queue.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True, name="audio-player-skip-ui")
        self._started = threading.Event()
        self._failed = False
        self._thread.start()
        self._started.wait(timeout=2)

    def _run(self) -> None:
        try:
            import tkinter as tk

            root = tk.Tk()
            root.title("Playback Control")
            root.geometry("260x110")
            root.resizable(False, False)

            label = tk.Label(root, text="Идет серверное воспроизведение")
            label.pack(pady=(12, 6))

            button = tk.Button(root, text="Пропустить", width=20)
            button.pack(pady=(0, 12))
            button.pack_forget()

            def on_skip() -> None:
                button.configure(state="disabled")
                self._skip_callback()

            button.configure(command=on_skip)

            def poll_events() -> None:
                try:
                    while True:
                        event = self._events.get_nowait()
                        if event == "show":
                            button.configure(state="normal")
                            if not button.winfo_ismapped():
                                button.pack(pady=(0, 12))
                            root.deiconify()
                            root.lift()
                        elif event == "hide":
                            button.pack_forget()
                            root.withdraw()
                        elif event == "shutdown":
                            root.destroy()
                            return
                except queue.Empty:
                    pass
                root.after(80, poll_events)

            root.withdraw()
            self._started.set()
            root.after(80, poll_events)
            root.mainloop()
        except Exception as exc:  # Tk may be unavailable in headless environments
            self._failed = True
            print(f"[player] Skip UI is unavailable: {exc}")
            self._started.set()

    def on_playback_start(self) -> None:
        if not self._failed:
            self._events.put("show")

    def on_playback_finish(self) -> None:
        if not self._failed:
            self._events.put("hide")

    def stop(self) -> None:
        if not self._failed:
            self._events.put("shutdown")
            self._thread.join(timeout=2)


@dataclass
class PlaybackRequest:
    """Represents a playback request in the queue."""

    data: bytes
    ffplay_bin: str
    volume: float
    show_skip_window: bool = False


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
        self._skip_window: Optional[_TkSkipWindowController | _NoopSkipWindowController] = None
        self._ui_lock = threading.Lock()
        self._lock = threading.Lock()
        self._initialized = True
        self._start_worker()

    def _start_worker(self) -> None:
        """Start the background worker thread that processes the queue."""
        self._worker_thread = threading.Thread(target=self._worker, daemon=True, name="audio-player-worker")
        self._worker_thread.start()

    def _get_skip_window(self):
        with self._ui_lock:
            if self._skip_window is None:
                controller = _TkSkipWindowController(self.skip)
                if controller._failed:
                    self._skip_window = _NoopSkipWindowController()
                else:
                    self._skip_window = controller
            return self._skip_window

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
        skip_window = None
        try:
            if req.show_skip_window:
                skip_window = self._get_skip_window()
                skip_window.on_playback_start()

            volume_int = int(req.volume * 256)
            cmd = [
                req.ffplay_bin,
                "-hide_banner",
                "-loglevel",
                "quiet",
                "-nodisp",
                "-autoexit",
                "-volume",
                str(volume_int),
                "-i",
                "pipe:0",
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
            assert proc.stdin is not None
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
            print(
                f"[player] Warning: ffplay not found at '{req.ffplay_bin}'. "
                "Install ffmpeg package (includes ffplay)."
            )
        except Exception as e:
            print(f"[player] Error during playback: {e}")
        finally:
            if skip_window is not None:
                skip_window.on_playback_finish()
            with self._lock:
                if self._current_proc is proc:
                    self._current_proc = None

    def play(self, data: bytes, ffplay_bin: str = "ffplay", volume: float = 1.0, show_skip_window: bool = False) -> None:
        """
        Queue audio for playback.

        Args:
            data: Audio bytes (WAV, MP3, etc.)
            ffplay_bin: Path to ffplay executable
            volume: Volume (0.0-10.0, 1.0 = 100%)
            show_skip_window: Show Tkinter control window with Skip button while track is playing
        """
        req = PlaybackRequest(data=data, ffplay_bin=ffplay_bin, volume=volume, show_skip_window=show_skip_window)
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
        with self._ui_lock:
            if self._skip_window is not None:
                self._skip_window.stop()
                self._skip_window = None


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


def play_audio(data: bytes, ffplay_bin: str = "ffplay", volume: float = 1.0, show_skip_window: bool = False) -> None:
    """
    Queue audio for playback (non-blocking).

    Audio will be played sequentially with other queued items.

    Args:
        data: Audio bytes (WAV, MP3, etc.)
        ffplay_bin: Path to ffplay executable
        volume: Volume (0.0-10.0, 1.0 = 100%)
        show_skip_window: Show Tkinter control window with Skip button while track is playing
    """
    _get_player().play(data, ffplay_bin, volume, show_skip_window)


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
