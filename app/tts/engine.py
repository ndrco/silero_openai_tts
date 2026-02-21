import io
import logging
import os
from pathlib import Path

import numpy as np
import soundfile as sf

log = logging.getLogger("silero")


class SileroTTSEngine:
    def __init__(self, language: str, model_id: str, device: str, sample_rate: int, default_speaker: str, num_threads: int = 0, max_chars_per_chunk: int = 500, chunk_pause_sec: float = 0.0, models_dir: str = "models"):
        self.language = language
        self.model_id = model_id
        self.device_mode = (device or "auto").lower()  # auto|cpu|cuda
        self.sample_rate = int(sample_rate)
        self.default_speaker = default_speaker
        self.num_threads = int(num_threads)
        self.max_chars_per_chunk = max(1, int(max_chars_per_chunk))
        self.chunk_pause_sec = max(0.0, float(chunk_pause_sec))
        self.models_dir = Path(models_dir).expanduser()

        self._torch = None
        self.device = None

        self._model = None
        self._symbols = None
        self._apply_tts = None

    def _resolve_device(self):
        torch = self._torch
        if self.device_mode == "cpu":
            return torch.device("cpu")
        if self.device_mode == "cuda":
            if not torch.cuda.is_available():
                raise RuntimeError("SILERO_DEVICE=cuda specified, but torch.cuda.is_available() == False")
            return torch.device("cuda")

        # auto
        if torch.cuda.is_available():
            return torch.device("cuda")
        return torch.device("cpu")

    def load(self):
        try:
            import torch
        except ImportError as e:
            raise RuntimeError(
                "PyTorch (torch) is not installed.\n"
                "CPU:  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu\n"
                "CUDA: pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126  (example)"
            ) from e

        self._torch = torch
        self.device = self._resolve_device()

        if self.num_threads > 0:
            torch.set_num_threads(self.num_threads)
            log.info("Silero torch.set_num_threads(%s)", self.num_threads)

        # Device logs
        if self.device.type == "cuda":
            gpu_name = torch.cuda.get_device_name(0)
            log.info("Silero device: CUDA (%s)", gpu_name)
            log.info("Torch CUDA runtime: %s", torch.version.cuda)
        else:
            log.info("Silero device: CPU")

        log.info("Loading Silero model: language=%s speaker_model=%s sample_rate=%s",
                 self.language, self.model_id, self.sample_rate)

        self.models_dir.mkdir(parents=True, exist_ok=True)
        os.environ["TORCH_HOME"] = str(self.models_dir.resolve())

        log.info("Silero model cache directory: %s", self.models_dir.resolve())

        # One hub.load call: repo may return 5 values (new API) or 2 (old API)
        result = torch.hub.load(
            repo_or_dir="snakers4/silero-models",
            model="silero_tts",
            language=self.language,
            speaker=self.model_id,
        )
        if len(result) == 5:
            model, symbols, _sr, _example_text, apply_tts = result
            # Some torch hub model `.to()` implementations work in-place
            # and may return None, so we do not rely on the return value.
            model.to(self.device)
            self._model = model
            self._symbols = symbols
            self._apply_tts = apply_tts
            log.info("Silero loaded (apply_tts API).")
        else:
            model, _ = result
            model.to(self.device)
            self._model = model
            self._apply_tts = None
            self._symbols = None
            log.info("Silero loaded (model.apply_tts API).")

    @staticmethod
    def _split_long_text(text: str, max_chars: int) -> list[str]:
        """Splits long text into chunks no longer than max_chars, by sentence or word boundaries."""
        text = (text or "").strip()
        if not text or len(text) <= max_chars:
            return [text] if text else []

        chunks = []
        while text:
            if len(text) <= max_chars:
                chunks.append(text.strip())
                break
            # Search boundary only within first max_chars (not max_chars+1) so chunk does not exceed the limit
            piece = text[:max_chars]
            last_sent = max(
                piece.rfind("."), piece.rfind("!"), piece.rfind("?"), piece.rfind("\n")
            )
            if last_sent >= 0:
                chunk = text[: last_sent + 1].strip()
                text = text[last_sent + 1 :].lstrip()
            else:
                last_space = piece.rfind(" ")
                if last_space >= 0:
                    chunk = text[: last_space + 1].strip()
                    text = text[last_space + 1 :].lstrip()
                else:
                    chunk = text[:max_chars].strip()
                    text = text[max_chars:].lstrip()
            if chunk:
                # Edge-case safeguard: do not pass chunks longer than the limit
                if len(chunk) > max_chars:
                    chunk = chunk[:max_chars].rstrip()
                if chunk:
                    chunks.append(chunk)
        return chunks

    def _synthesize_chunk(self, text: str, speaker: str) -> np.ndarray:
        """Synthesizes one text fragment and returns a float32 mono array."""
        torch = self._torch
        with torch.inference_mode():
            if self._apply_tts is not None:
                audio = self._apply_tts(
                    texts=[text],
                    model=self._model,
                    sample_rate=self.sample_rate,
                    symbols=self._symbols,
                    device=self.device,
                )[0]
                return audio.detach().cpu().numpy().astype(np.float32)
            return (
                self._model.apply_tts(
                    text=text,
                    speaker=speaker,
                    sample_rate=self.sample_rate,
                )
                .detach()
                .cpu()
                .numpy()
                .astype(np.float32)
            )

    def synthesize_wav_bytes(self, text: str, speaker: str | None = None) -> bytes:
        if self._model is None or self._torch is None:
            raise RuntimeError("Silero model is not loaded")

        spk = speaker or self.default_speaker
        chunks = self._split_long_text(text, self.max_chars_per_chunk)
        if not chunks:
            # Empty text -> minimal silence
            chunks = [" "]

        if len(chunks) > 1:
            log.debug("Silero long text split into %s chunks", len(chunks))

        parts = [self._synthesize_chunk(chunk, spk) for chunk in chunks]
        if len(parts) > 1 and self.chunk_pause_sec > 0:
            silence = np.zeros(int(self.sample_rate * self.chunk_pause_sec), dtype=np.float32)
            audio_parts = []
            for i, p in enumerate(parts):
                audio_parts.append(p)
                if i < len(parts) - 1:
                    audio_parts.append(silence)
            audio_np = np.concatenate(audio_parts, axis=0)
        else:
            audio_np = np.concatenate(parts, axis=0)

        buf = io.BytesIO()
        sf.write(buf, audio_np, self.sample_rate, format="WAV", subtype="PCM_16")
        return buf.getvalue()
