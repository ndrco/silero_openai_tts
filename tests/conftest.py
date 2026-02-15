"""API test fixtures: test app with a mock engine (without loading Silero)."""
import io
import tempfile

import numpy as np
import pytest
import soundfile as sf
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes_tts import router as tts_router
from app.audio.cache import DiskCache
from app.settings import Settings
from app.text.language_router import LanguageAwareRouter
from app.text.normalize import TextNormalizer


def _minimal_wav_bytes(sample_rate: int = 48000) -> bytes:
    """Minimal valid WAV (silence ~10 ms) for tests."""
    buf = io.BytesIO()
    samples = np.zeros(int(sample_rate * 0.01), dtype=np.float32)
    sf.write(buf, samples, sample_rate, format="WAV", subtype="PCM_16")
    return buf.getvalue()


class MockSileroEngine:
    """Mock TTS engine: does not load a model, returns a short WAV."""

    default_speaker = "baya"
    sample_rate = 48000

    def __init__(self, default_speaker: str = "baya") -> None:
        self.default_speaker = default_speaker
        self.calls: list[tuple[str, str | None]] = []

    def load(self) -> None:
        pass

    def synthesize_wav_bytes(self, text: str, speaker: str | None = None) -> bytes:
        self.calls.append((text, speaker))
        return _minimal_wav_bytes(self.sample_rate)


def create_test_app(*, require_auth: bool = False, cache_dir: str | None = None, language_aware_routing: bool = False) -> FastAPI:
    """Creates a FastAPI test app with a mock engine."""
    app = FastAPI(title="Silero TTS Test", version="0.1.0")
    app.include_router(tts_router)

    cache_path = cache_dir or tempfile.mkdtemp(prefix="silero_tts_test_cache_")
    settings = Settings(
        require_auth=require_auth,
        api_key="test-secret-key",
        cache_dir=cache_path,
        cache_max_files=100,
        ffmpeg_bin="ffmpeg",
        language_aware_routing=language_aware_routing,
    )

    app.state.settings = settings
    app.state.engine = MockSileroEngine(default_speaker="baya")
    app.state.en_engine = MockSileroEngine(default_speaker="en_0") if language_aware_routing else None
    app.state.normalizer = TextNormalizer(transliterate_latin=not language_aware_routing)
    app.state.en_normalizer = TextNormalizer(transliterate_latin=False, expand_numeric=False) if language_aware_routing else None
    app.state.language_router = LanguageAwareRouter() if language_aware_routing else None
    app.state.cache = DiskCache(settings.cache_dir, max_files=settings.cache_max_files)

    return app


@pytest.fixture
def app():
    """App without authentication."""
    return create_test_app(require_auth=False)


@pytest.fixture
def app_with_auth():
    """App with authentication enabled."""
    return create_test_app(require_auth=True)


@pytest.fixture
def app_with_routing():
    """App with language-aware routing."""
    return create_test_app(require_auth=False, language_aware_routing=True)


@pytest.fixture
def client(app: FastAPI):
    """HTTP client for the app without authentication."""
    return TestClient(app)


@pytest.fixture
def client_with_auth(app_with_auth: FastAPI):
    """HTTP client for the app with authentication."""
    return TestClient(app_with_auth)


@pytest.fixture
def client_with_routing(app_with_routing: FastAPI):
    """HTTP client for the app with language-aware routing."""
    return TestClient(app_with_routing)


@pytest.fixture
def valid_speech_payload():
    """Valid request body for POST /v1/audio/speech."""
    return {
        "model": "gpt-4o-mini-tts",
        "voice": "alloy",
        "input": "Привет, мир.",
        "response_format": "wav",
        "speed": 1.0,
    }
