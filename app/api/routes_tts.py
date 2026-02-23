import logging
import hashlib
from io import BytesIO
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from app.api.schemas import SpeechRequest
from app.tts.voices import map_voice_to_silero
from app.audio.encode import encode_audio, media_type_for
from app.audio.player import play_audio, skip_playback

router = APIRouter()
log = logging.getLogger("silero")


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

    settings = request.app.state.settings
    engine = request.app.state.engine
    cache = request.app.state.cache
    tts_service = request.app.state.tts_service

    # Print text to console if show_text or force_play is enabled
    if settings.show_text or settings.force_play:
        log.info("[TTS] Text: %s", payload.input.strip())

    silero_speaker = map_voice_to_silero(payload.voice, default=engine.default_speaker)
    out_fmt = payload.response_format or "wav"

    key_src = (
        f"lar={settings.language_aware_routing}|voice={silero_speaker}|speed={payload.speed}|"
        f"fmt={out_fmt}|sr={engine.sample_rate}|text={payload.input.strip()}"
    )
    key = hashlib.sha256(key_src.encode("utf-8")).hexdigest()

    cached = cache.get(key)
    if cached is not None:
        return StreamingResponse(BytesIO(cached), media_type=media_type_for(out_fmt))

    wav_bytes = tts_service.synthesize(payload.input, silero_speaker)

    out_bytes = encode_audio(
        wav_bytes=wav_bytes,
        out_format=out_fmt,
        ffmpeg_bin=request.app.state.settings.ffmpeg_bin,
        speed=payload.speed or 1.0,
    )

    cache.put(key, out_bytes)

    # Auto-play on the server side (use original WAV for better quality)
    # force_play overrides auto_play setting
    if settings.auto_play or settings.force_play:
        # Apply only speed to WAV for playback
        wav_for_play = encode_audio(
            wav_bytes=wav_bytes,
            out_format="wav",
            ffmpeg_bin=request.app.state.settings.ffmpeg_bin,
            speed=payload.speed or 1.0,
        )
        play_audio(
            wav_for_play,
            ffplay_bin=settings.ffplay_bin,
            volume=settings.auto_play_volume,
            show_skip_window=settings.auto_play_show_skip_window,
        )

    return StreamingResponse(BytesIO(out_bytes), media_type=media_type_for(out_fmt))


@router.delete("/v1/audio/speech/skip")
def skip_speech(request: Request):
    """Skip the currently playing audio."""
    _check_auth(request)
    skipped = skip_playback()
    return {"skipped": skipped}
