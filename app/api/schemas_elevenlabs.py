from typing import Literal

from pydantic import BaseModel, Field


ElevenLabsOutputFormat = Literal[
    "mp3_22050_32",
    "mp3_44100_64",
    "mp3_44100_128",
    "pcm_16000",
    "pcm_22050",
    "pcm_24000",
]


class ElevenLabsVoiceSettings(BaseModel):
    stability: float | None = Field(default=None, ge=0.0, le=1.0)
    similarity_boost: float | None = Field(default=None, ge=0.0, le=1.0)
    style: float | None = Field(default=None, ge=0.0, le=1.0)
    use_speaker_boost: bool | None = None


class ElevenLabsSpeechRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4096)
    model_id: str | None = None
    voice_settings: ElevenLabsVoiceSettings | None = None
    output_format: ElevenLabsOutputFormat | None = "mp3_44100_128"
