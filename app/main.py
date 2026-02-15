import logging
import shutil
from fastapi import FastAPI
from app.settings import Settings
from app.tts.engine import SileroTTSEngine
from app.text.normalize import TextNormalizer
from app.text.language_router import LanguageAwareRouter
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

    ru_engine = SileroTTSEngine(
        language=settings.silero_language,
        model_id=settings.silero_model_id,
        device=settings.silero_device,
        sample_rate=settings.silero_sample_rate,
        default_speaker=settings.silero_default_speaker,
        num_threads=settings.silero_num_threads,
        max_chars_per_chunk=settings.silero_max_chars_per_chunk,
        chunk_pause_sec=settings.silero_pause_between_fragments_sec,
        models_dir=settings.silero_models_dir,
    )

    en_engine = None
    if settings.language_aware_routing and settings.silero_en_enabled:
        en_engine = SileroTTSEngine(
            language=settings.silero_en_language,
            model_id=settings.silero_en_model_id,
            device=settings.silero_device,
            sample_rate=settings.silero_en_sample_rate,
            default_speaker=settings.silero_en_default_speaker,
            num_threads=settings.silero_num_threads,
            max_chars_per_chunk=settings.silero_max_chars_per_chunk,
            chunk_pause_sec=settings.silero_pause_between_fragments_sec,
            models_dir=settings.silero_models_dir,
        )

    if settings.language_aware_routing:
        # In language-aware mode, transliteration is disabled,
        # so EN segments are not converted into Cyrillic.
        ru_normalizer = TextNormalizer(transliterate_latin=False)
        en_normalizer = TextNormalizer(transliterate_latin=False, expand_numeric=True, expand_numeric_lang="en")
        lang_router = LanguageAwareRouter()
    else:
        ru_normalizer = TextNormalizer(transliterate_latin=settings.transliterate_latin)
        en_normalizer = None
        lang_router = None

    cache = DiskCache(settings.cache_dir, max_files=settings.cache_max_files)

    app.state.settings = settings
    app.state.engine = ru_engine
    app.state.en_engine = en_engine
    app.state.normalizer = ru_normalizer
    app.state.en_normalizer = en_normalizer
    app.state.language_router = lang_router
    app.state.cache = cache

    @app.on_event("shutdown")
    def _shutdown():
        cache_dir = app.state.settings.cache_dir
        try:
            shutil.rmtree(cache_dir)
            logging.getLogger("silero").info("Cache cleared: %s", cache_dir)
        except OSError as e:
            logging.getLogger("silero").warning("Could not remove cache dir %s: %s", cache_dir, e)

    # Load model(s) immediately on app creation to avoid dependency on startup order
    ru_engine.load()
    if en_engine is not None:
        en_engine.load()

    app.include_router(tts_router)
    return app


app = create_app()
