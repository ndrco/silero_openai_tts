from pydantic_settings import BaseSettings
from typing import Literal

DeviceMode = Literal["auto", "cpu", "cuda"]

class Settings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    
    silero_language: str = "ru"
    silero_model_id: str = "v4_ru"
    silero_sample_rate: int = 48000

    # было: "cpu"
    silero_device: DeviceMode = "auto"
    silero_default_speaker: str = "baya"

    require_auth: bool = False
    api_key: str = "dummy-local-key"

    cache_dir: str = ".cache_tts"
    cache_max_files: int = 2000

    ffmpeg_bin: str = "ffmpeg"

    class Config:
        env_file = ".env"
        extra = "ignore"
