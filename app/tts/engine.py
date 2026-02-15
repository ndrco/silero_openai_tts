import io
import logging
import numpy as np
import soundfile as sf

log = logging.getLogger("silero")

class SileroTTSEngine:
    def __init__(self, language: str, model_id: str, device: str, sample_rate: int, default_speaker: str):
        self.language = language
        self.model_id = model_id
        self.device_mode = (device or "auto").lower()  # auto|cpu|cuda
        self.sample_rate = int(sample_rate)
        self.default_speaker = default_speaker

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
                raise RuntimeError("SILERO_DEVICE=cuda задан, но torch.cuda.is_available() == False")
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
                "PyTorch (torch) не установлен.\n"
                "CPU:  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu\n"
                "CUDA: pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126  (пример)"
            ) from e

        self._torch = torch
        self.device = self._resolve_device()

        # Логи про устройство
        if self.device.type == "cuda":
            gpu_name = torch.cuda.get_device_name(0)
            log.info("Silero device: CUDA (%s)", gpu_name)
            log.info("Torch CUDA runtime: %s", torch.version.cuda)
        else:
            log.info("Silero device: CPU")

        log.info("Loading Silero model: language=%s speaker_model=%s sample_rate=%s",
                 self.language, self.model_id, self.sample_rate)

        # Один вызов hub.load: репо может вернуть 5 (новый API) или 2 (старый API)
        result = torch.hub.load(
            repo_or_dir="snakers4/silero-models",
            model="silero_tts",
            language=self.language,
            speaker=self.model_id,
        )
        if len(result) == 5:
            model, symbols, _sr, _example_text, apply_tts = result
            self._model = model.to(self.device)
            self._symbols = symbols
            self._apply_tts = apply_tts
            log.info("Silero loaded (apply_tts API).")
        else:
            model, _ = result
            self._model = model.to(self.device)
            self._apply_tts = None
            self._symbols = None
            log.info("Silero loaded (model.apply_tts API).")

    def synthesize_wav_bytes(self, text: str, speaker: str | None = None) -> bytes:
        if self._model is None or self._torch is None:
            raise RuntimeError("Silero model is not loaded")

        torch = self._torch
        spk = speaker or self.default_speaker

        with torch.inference_mode():
            if self._apply_tts is not None:
                audio = self._apply_tts(
                    texts=[text],
                    model=self._model,
                    sample_rate=self.sample_rate,
                    symbols=self._symbols,
                    device=self.device,
                )[0]
                audio_np = audio.detach().cpu().numpy().astype(np.float32)
            else:
                audio_np = self._model.apply_tts(
                    text=text,
                    speaker=spk,
                    sample_rate=self.sample_rate,
                ).detach().cpu().numpy().astype(np.float32)

        buf = io.BytesIO()
        sf.write(buf, audio_np, self.sample_rate, format="WAV", subtype="PCM_16")
        return buf.getvalue()
