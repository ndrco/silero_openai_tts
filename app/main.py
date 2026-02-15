import logging
import shutil
from fastapi import FastAPI
from app.settings import Settings
from app.tts.engine import SileroTTSEngine
from app.text.normalize import TextNormalizer
from app.audio.cache import DiskCache
from app.api.routes_tts import router as tts_router

def create_app() -> FastAPI:
    settings = Settings()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    logging.getLogger("silero").info("Starting app...")
    logging.getLogger("silero").info("SILERO_DEVICE mode: %s", settings.silero_device)
    if settings.ffmpeg_bin:
        if shutil.which(settings.ffmpeg_bin) is None:
            logging.getLogger("silero").warning(
                "ffmpeg not found in PATH. Non-WAV formats and speed change will not work."
            )

    app = FastAPI(title="Silero OpenAI-compatible TTS", version="0.1.0")

    engine = SileroTTSEngine(
        language=settings.silero_language,
        model_id=settings.silero_model_id,
        device=settings.silero_device,
        sample_rate=settings.silero_sample_rate,
        default_speaker=settings.silero_default_speaker,
        num_threads=settings.silero_num_threads,
        max_chars_per_chunk=settings.silero_max_chars_per_chunk,
    )
    normalizer = TextNormalizer(transliterate_latin=settings.transliterate_latin)
    cache = DiskCache(settings.cache_dir, max_files=settings.cache_max_files)

    app.state.settings = settings
    app.state.engine = engine
    app.state.normalizer = normalizer
    app.state.cache = cache

    # Загружаем модель сразу при создании app, чтобы не зависеть от порядка startup
    engine.load()

    app.include_router(tts_router)
    return app

app = create_app()
