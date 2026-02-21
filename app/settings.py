from pydantic_settings import BaseSettings
from typing import Literal

DeviceMode = Literal["auto", "cpu", "cuda"]

class Settings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    
    silero_language: str = "ru"
    silero_model_id: str = "v5_1_ru"
    silero_sample_rate: int = 48000

    silero_device: DeviceMode = "auto"
    silero_default_speaker: str = "kseniya"
    silero_num_threads: int = 4  # 0 = do not change; otherwise torch.set_num_threads(N)
    silero_max_chars_per_chunk: int = 500  # max chars per chunk for long text
    silero_pause_between_fragments_sec: float = 0.3  # pause between chunks/segments (sec)
    silero_models_dir: str = "models"  # persistent directory for Silero cache/models (torch.hub)

    require_auth: bool = False
    api_key: str = "dummy-local-key"

    cache_dir: str = ".cache_tts"
    cache_max_files: int = 2000

    ffmpeg_bin: str = "ffmpeg"
    ffplay_bin: str = "ffplay.exe"  # Windows ffplay for WSL2 compatibility
    auto_play: bool = True  # auto-play audio on the server side
    auto_play_volume: float = 1.0  # auto-play volume (1.0 = 100%)

    transliterate_latin: bool = True  # Latin → Cyrillic transliteration for pronouncing English words

    language_aware_routing: bool = True

    silero_en_enabled: bool = True
    silero_en_language: str = "en"
    silero_en_model_id: str = "v3_en"
    silero_en_sample_rate: int = 48000
    silero_en_default_speaker: str = "en_21"

    class Config:
        env_file = ".env"
        extra = "ignore"
