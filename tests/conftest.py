"""Фикстуры для тестов API: тестовое приложение с мок-движком (без загрузки Silero)."""
import io
import tempfile
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes_tts import router as tts_router
from app.audio.cache import DiskCache
from app.settings import Settings
from app.text.normalize import TextNormalizer


def _minimal_wav_bytes(sample_rate: int = 48000) -> bytes:
    """Минимальный валидный WAV (тишина ~10 ms) для тестов."""
    buf = io.BytesIO()
    samples = np.zeros(int(sample_rate * 0.01), dtype=np.float32)
    sf.write(buf, samples, sample_rate, format="WAV", subtype="PCM_16")
    return buf.getvalue()


class MockSileroEngine:
    """Мок движка TTS: не загружает модель, возвращает короткий WAV."""

    default_speaker = "baya"
    sample_rate = 48000

    def load(self) -> None:
        pass

    def synthesize_wav_bytes(self, text: str, speaker: str | None = None) -> bytes:
        return _minimal_wav_bytes(self.sample_rate)


def create_test_app(*, require_auth: bool = False, cache_dir: str | None = None) -> FastAPI:
    """Создаёт FastAPI-приложение для тестов с мок-движком."""
    app = FastAPI(title="Silero TTS Test", version="0.1.0")
    app.include_router(tts_router)

    cache_path = cache_dir or tempfile.mkdtemp(prefix="silero_tts_test_cache_")
    settings = Settings(
        require_auth=require_auth,
        api_key="test-secret-key",
        cache_dir=cache_path,
        cache_max_files=100,
        ffmpeg_bin="ffmpeg",
    )

    app.state.settings = settings
    app.state.engine = MockSileroEngine()
    app.state.normalizer = TextNormalizer()
    app.state.cache = DiskCache(settings.cache_dir, max_files=settings.cache_max_files)

    return app


@pytest.fixture
def app():
    """Приложение без авторизации."""
    return create_test_app(require_auth=False)


@pytest.fixture
def app_with_auth():
    """Приложение с включённой авторизацией."""
    return create_test_app(require_auth=True)


@pytest.fixture
def client(app: FastAPI):
    """HTTP-клиент для приложения без авторизации."""
    return TestClient(app)


@pytest.fixture
def client_with_auth(app_with_auth: FastAPI):
    """HTTP-клиент для приложения с авторизацией."""
    return TestClient(app_with_auth)


@pytest.fixture
def valid_speech_payload():
    """Валидное тело запроса для POST /v1/audio/speech."""
    return {
        "model": "gpt-4o-mini-tts",
        "voice": "alloy",
        "input": "Привет, мир.",
        "response_format": "wav",
        "speed": 1.0,
    }
