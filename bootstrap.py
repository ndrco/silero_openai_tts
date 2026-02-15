#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path

FILES: dict[str, str] = {}

FILES["pyproject.toml"] = r'''[project]
name = "silero-openai-tts"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
  "fastapi>=0.110",
  "uvicorn[standard]>=0.27",
  "pydantic>=2.5",
  "pydantic-settings>=2.1",
  "numpy>=1.23",
  "soundfile>=0.12",
  "num2words>=0.5",
  "pymorphy3>=2.0",
  "omegaconf>=2.0",
  "torch>=2.0",
]

[tool.uvicorn]
factory = false
'''

FILES[".env.example"] = r'''HOST=0.0.0.0
PORT=8000

SILERO_LANGUAGE=ru
SILERO_MODEL_ID=v4_ru
SILERO_SAMPLE_RATE=48000
SILERO_DEVICE=cpu
SILERO_DEFAULT_SPEAKER=baya
SILERO_MODELS_DIR=models

REQUIRE_AUTH=false
API_KEY=dummy-local-key

CACHE_DIR=.cache_tts
CACHE_MAX_FILES=2000

FFMPEG_BIN=ffmpeg
'''

FILES["README.md"] = r'''### WSL2 deps
sudo apt-get update
sudo apt-get install -y ffmpeg libsndfile1

### venv
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .

### run
# Better create .env based on .env.example
uvicorn app.main:app --host 0.0.0.0 --port 8000

### test
curl http://localhost:8000/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini-tts","voice":"alloy","input":"У меня 5 запросов и 21 рубль.","response_format":"mp3","speed":1.1}' \
  --output out.mp3
'''

FILES["app/__init__.py"] = ""

FILES["app/settings.py"] = r'''from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000

    silero_language: str = "ru"
    silero_model_id: str = "v4_ru"
    silero_sample_rate: int = 48000
    silero_device: str = "cpu"
    silero_num_threads: int = 0
    silero_default_speaker: str = "baya"
    silero_models_dir: str = "models"

    require_auth: bool = False
    api_key: str = "dummy-local-key"

    cache_dir: str = ".cache_tts"
    cache_max_files: int = 2000

    ffmpeg_bin: str = "ffmpeg"

    class Config:
        env_file = ".env"
        extra = "ignore"
'''

FILES["app/main.py"] = r'''from fastapi import FastAPI
from app.settings import Settings
from app.tts.engine import SileroTTSEngine
from app.text.normalize import TextNormalizer
from app.audio.cache import DiskCache
from app.api.routes_tts import router as tts_router

def create_app() -> FastAPI:
    settings = Settings()

    app = FastAPI(title="Silero OpenAI-compatible TTS", version="0.1.0")

    engine = SileroTTSEngine(
        language=settings.silero_language,
        model_id=settings.silero_model_id,
        device=settings.silero_device,
        sample_rate=settings.silero_sample_rate,
        default_speaker=settings.silero_default_speaker,
        num_threads=settings.silero_num_threads,
        models_dir=settings.silero_models_dir,
    )
    normalizer = TextNormalizer()
    cache = DiskCache(settings.cache_dir, max_files=settings.cache_max_files)

    app.state.settings = settings
    app.state.engine = engine
    app.state.normalizer = normalizer
    app.state.cache = cache

    @app.on_event("startup")
    def _startup():
        engine.load()

    app.include_router(tts_router)
    return app

app = create_app()
'''

FILES["app/api/__init__.py"] = ""
FILES["app/api/schemas.py"] = r'''from pydantic import BaseModel, Field
from typing import Literal, Optional

AudioFormat = Literal["wav", "mp3", "opus", "aac", "flac"]

class SpeechRequest(BaseModel):
    model: str = Field(..., description="OpenAI-compatible field")
    input: str = Field(..., min_length=1, max_length=4096)
    voice: str = Field(..., description="OpenAI voice name or Silero speaker")
    response_format: Optional[AudioFormat] = "wav"
    speed: Optional[float] = Field(1.0, ge=0.25, le=4.0)
'''

FILES["app/api/routes_tts.py"] = r'''import hashlib
from io import BytesIO
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from app.api.schemas import SpeechRequest
from app.tts.voices import map_voice_to_silero
from app.audio.encode import encode_audio, media_type_for

router = APIRouter()

def _check_auth(req: Request):
    settings = req.app.state.settings
    if not settings.require_auth:
        return
    auth = req.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization Bearer token")
    token = auth.split(" ", 1)[1].strip()
    if token != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

@router.post("/v1/audio/speech")
def create_speech(payload: SpeechRequest, request: Request):
    _check_auth(request)

    engine = request.app.state.engine
    normalizer = request.app.state.normalizer
    cache = request.app.state.cache

    normalized = normalizer.run(payload.input)
    silero_speaker = map_voice_to_silero(payload.voice, default=engine.default_speaker)
    out_fmt = payload.response_format or "wav"

    key_src = f"{silero_speaker}|{payload.speed}|{out_fmt}|{engine.sample_rate}|{normalized}"
    key = hashlib.sha256(key_src.encode("utf-8")).hexdigest()

    cached = cache.get(key)
    if cached is not None:
        return StreamingResponse(BytesIO(cached), media_type=media_type_for(out_fmt))

    wav_bytes = engine.synthesize_wav_bytes(normalized, speaker=silero_speaker)

    out_bytes = encode_audio(
        wav_bytes=wav_bytes,
        out_format=out_fmt,
        ffmpeg_bin=request.app.state.settings.ffmpeg_bin,
        speed=payload.speed or 1.0,
    )

    cache.put(key, out_bytes)
    return StreamingResponse(BytesIO(out_bytes), media_type=media_type_for(out_fmt))
'''

FILES["app/tts/__init__.py"] = ""
FILES["app/tts/voices.py"] = r'''OPENAI_TO_SILERO = {
    "alloy": "baya",
    "echo": "aidar",
    "fable": "kseniya",
    "onyx": "eugene",
    "nova": "xenia",
    "shimmer": "baya",
}

KNOWN_SILERO_SPEAKERS = {"aidar", "baya", "kseniya", "xenia", "eugene", "random"}

def map_voice_to_silero(voice: str, default: str = "baya") -> str:
    v = (voice or "").strip().lower()
    if v in KNOWN_SILERO_SPEAKERS:
        return v
    return OPENAI_TO_SILERO.get(v, default)
'''

FILES["app/tts/engine.py"] = r'''import io
import numpy as np
import torch
import soundfile as sf

class SileroTTSEngine:
    def __init__(self, language: str, model_id: str, device: str, sample_rate: int, default_speaker: str):
        self.language = language
        self.model_id = model_id
        self.device = torch.device(device)
        self.sample_rate = int(sample_rate)
        self.default_speaker = default_speaker
        self._model = None
        self._symbols = None
        self._apply_tts = None

    def load(self):
        # New-style: returns apply_tts callable
        try:
            model, symbols, sample_rate, example_text, apply_tts = torch.hub.load(
                repo_or_dir="snakers4/silero-models",
                model="silero_tts",
                language=self.language,
                speaker=self.model_id,
            )
            self._model = model.to(self.device)
            self._symbols = symbols
            self._apply_tts = apply_tts
            return
        except Exception:
            pass

        # Old-style: model.apply_tts(...)
        model, _ = torch.hub.load(
            repo_or_dir="snakers4/silero-models",
            model="silero_tts",
            language=self.language,
            speaker=self.model_id,
        )
        self._model = model.to(self.device)

    @torch.inference_mode()
    def synthesize_wav_bytes(self, text: str, speaker: str | None = None) -> bytes:
        if self._model is None:
            raise RuntimeError("Silero model is not loaded")
        spk = speaker or self.default_speaker

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
'''

FILES["app/text/__init__.py"] = ""
FILES["app/text/normalize.py"] = r'''from app.text.numbers import expand_numbers

class TextNormalizer:
    def run(self, text: str) -> str:
        t = (text or "").strip()
        if not t:
            return t
        t = expand_numbers(t)
        t = " ".join(t.split())
        return t
'''

FILES["app/text/morph.py"] = r'''import pymorphy3

_morph = pymorphy3.MorphAnalyzer(lang="ru")

def _best_noun_parse(word: str):
    parses = _morph.parse(word)
    for p in parses:
        if p.tag.POS == "NOUN":
            return p
    return parses[0] if parses else None

def agree_word_with_number(word: str, n: int) -> str:
    p = _best_noun_parse(word)
    if p is None:
        return word
    agreed = p.make_agree_with_number(n)
    return agreed.word if agreed else word

def match_case(template: str, word: str) -> str:
    if template.isupper():
        return word.upper()
    if template.istitle():
        return word[:1].upper() + word[1:]
    return word
'''

FILES["app/text/numbers.py"] = r'''import re
from num2words import num2words
from app.text.morph import agree_word_with_number, match_case

NUM_NOUN_RE = re.compile(r"(?<!\w)(\d{1,18})\s+([А-Яа-яЁё]+)(?!\w)")
PERCENT_RE = re.compile(r"(?<!\w)(\d{1,18})\s*%(?!\w)")
RUBLE_RE = re.compile(r"(?<!\w)(\d{1,18})\s*(₽|руб\.?|рубля|рублей|рубль)(?!\w)", re.IGNORECASE)
STANDALONE_INT_RE = re.compile(r"(?<!\d\.)\b(\d{1,18})\b(?![.:]\d)")

def _num_to_words_ru(n: int) -> str:
    return num2words(n, lang="ru").replace("-", " ")

def expand_numbers(text: str) -> str:
    def repl_num_noun(m: re.Match) -> str:
        n = int(m.group(1))
        noun = m.group(2)
        noun2 = agree_word_with_number(noun.lower(), n)
        noun2 = match_case(noun, noun2)
        return f"{_num_to_words_ru(n)} {noun2}"

    text = NUM_NOUN_RE.sub(repl_num_noun, text)

    def repl_percent(m: re.Match) -> str:
        n = int(m.group(1))
        noun2 = agree_word_with_number("процент", n)
        return f"{_num_to_words_ru(n)} {noun2}"

    text = PERCENT_RE.sub(repl_percent, text)

    def repl_ruble(m: re.Match) -> str:
        n = int(m.group(1))
        noun2 = agree_word_with_number("рубль", n)
        return f"{_num_to_words_ru(n)} {noun2}"

    text = RUBLE_RE.sub(repl_ruble, text)

    def repl_standalone(m: re.Match) -> str:
        n = int(m.group(1))
        return _num_to_words_ru(n)

    text = STANDALONE_INT_RE.sub(repl_standalone, text)
    return text
'''

FILES["app/audio/__init__.py"] = ""
FILES["app/audio/cache.py"] = r'''from __future__ import annotations
import os
from pathlib import Path

class DiskCache:
    def __init__(self, root: str, max_files: int = 2000):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.max_files = int(max_files)

    def _path(self, key: str) -> Path:
        return self.root / key[:2] / (key[2:4]) / f"{key}.bin"

    def get(self, key: str) -> bytes | None:
        p = self._path(key)
        if not p.exists():
            return None
        return p.read_bytes()

    def put(self, key: str, data: bytes) -> None:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        self._gc()

    def _gc(self):
        files = []
        for dirpath, _, filenames in os.walk(self.root):
            for fn in filenames:
                if fn.endswith(".bin"):
                    fp = Path(dirpath) / fn
                    files.append((fp.stat().st_mtime, fp))
        if len(files) <= self.max_files:
            return
        files.sort()
        for _, fp in files[: len(files) - self.max_files]:
            try:
                fp.unlink()
            except OSError:
                pass
'''

FILES["app/audio/encode.py"] = r'''import subprocess
from typing import Literal

AudioFormat = Literal["wav", "mp3", "opus", "aac", "flac"]

MEDIA_TYPES = {
    "wav": "audio/wav",
    "mp3": "audio/mpeg",
    "opus": "audio/ogg",
    "aac": "audio/aac",
    "flac": "audio/flac",
}

def media_type_for(fmt: AudioFormat) -> str:
    return MEDIA_TYPES.get(fmt, "application/octet-stream")

def _atempo_chain(speed: float) -> str:
    if speed <= 0:
        speed = 1.0
    filters = []
    s = float(speed)
    while s > 2.0:
        filters.append("atempo=2.0")
        s /= 2.0
    while s < 0.5:
        filters.append("atempo=0.5")
        s /= 0.5
    filters.append(f"atempo={s:.6f}")
    return ",".join(filters)

def encode_audio(wav_bytes: bytes, out_format: AudioFormat, ffmpeg_bin: str, speed: float = 1.0) -> bytes:
    if out_format == "wav" and abs(speed - 1.0) < 1e-6:
        return wav_bytes

    afilter = _atempo_chain(speed) if abs(speed - 1.0) > 1e-6 else None

    if out_format == "wav":
        # WAV with speed adjustment via ffmpeg
        args = [ffmpeg_bin, "-hide_banner", "-loglevel", "error", "-i", "pipe:0"]
        if afilter:
            args += ["-filter:a", afilter]
        args += ["-f", "wav", "pipe:1"]
    elif out_format == "mp3":
        args = [ffmpeg_bin, "-hide_banner", "-loglevel", "error", "-i", "pipe:0"]
        if afilter:
            args += ["-filter:a", afilter]
        args += ["-f", "mp3", "pipe:1"]

    elif out_format == "flac":
        args = [ffmpeg_bin, "-hide_banner", "-loglevel", "error", "-i", "pipe:0"]
        if afilter:
            args += ["-filter:a", afilter]
        args += ["-f", "flac", "pipe:1"]

    elif out_format == "aac":
        args = [ffmpeg_bin, "-hide_banner", "-loglevel", "error", "-i", "pipe:0"]
        if afilter:
            args += ["-filter:a", afilter]
        args += ["-c:a", "aac", "-f", "adts", "pipe:1"]

    elif out_format == "opus":
        args = [ffmpeg_bin, "-hide_banner", "-loglevel", "error", "-i", "pipe:0"]
        if afilter:
            args += ["-filter:a", afilter]
        args += ["-c:a", "libopus", "-f", "ogg", "pipe:1"]

    else:
        raise ValueError(f"Unsupported format: {out_format}")

    proc = subprocess.run(args, input=wav_bytes, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", errors="ignore")[:4000]
        raise RuntimeError(f"ffmpeg failed: {err}")
    return proc.stdout
'''

def ensure_parents(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

def write_file(path: Path, content: str) -> None:
    ensure_parents(path)
    if path.exists():
        # Do not overwrite existing files without your decision
        return
    path.write_text(content, encoding="utf-8")

def main() -> None:
    root = Path(".").resolve()
    for rel, content in FILES.items():
        write_file(root / rel, content)
    print("✅ Project skeleton created.")
    print("Next:")
    print("  sudo apt-get update && sudo apt-get install -y ffmpeg libsndfile1")
    print("  python -m venv .venv && source .venv/bin/activate")
    print("  pip install -U pip && pip install -e .")
    print("  uvicorn app.main:app --host 0.0.0.0 --port 8000")

if __name__ == "__main__":
    main()
