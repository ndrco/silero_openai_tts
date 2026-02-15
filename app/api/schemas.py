from pydantic import BaseModel, Field
from typing import Literal, Optional

AudioFormat = Literal["wav", "mp3", "opus", "aac", "flac"]

class SpeechRequest(BaseModel):
    model: str = Field(..., description="OpenAI-compatible field")
    input: str = Field(..., min_length=1, max_length=4096)
    voice: str = Field(..., description="OpenAI voice name or Silero speaker")
    response_format: Optional[AudioFormat] = "wav"
    speed: Optional[float] = Field(1.0, ge=0.25, le=4.0)
