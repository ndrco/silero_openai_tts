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
    silero_default_speaker: str = "baya"
    silero_num_threads: int = 4  # 0 = не менять; иначе torch.set_num_threads(N)
    silero_max_chars_per_chunk: int = 500  # макс. символов в чанке для длинного текста

    require_auth: bool = False
    api_key: str = "dummy-local-key"

    cache_dir: str = ".cache_tts"
    cache_max_files: int = 2000

    ffmpeg_bin: str = "ffmpeg"

    transliterate_latin: bool = True  # латиница → кириллица для озвучки английских слов

    class Config:
        env_file = ".env"
        extra = "ignore"
