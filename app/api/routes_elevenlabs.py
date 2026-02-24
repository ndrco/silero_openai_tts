import hashlib
import logging
from io import BytesIO

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.api.auth import check_auth
from app.api.schemas_elevenlabs import ElevenLabsSpeechRequest
from app.audio.encode import encode_audio, media_type_for
from app.tts.elevenlabs import (
    elevenlabs_output_to_internal_format,
    elevenlabs_voices_response,
    get_elevenlabs_voice_map,
    map_voice_id_to_silero,
)

router = APIRouter()
log = logging.getLogger("silero")


@router.get("/v1/voices")
def list_voices(request: Request):
    check_auth(request)
    settings = request.app.state.settings
    voice_map = get_elevenlabs_voice_map(settings.elevenlabs_voice_map_json)
    return elevenlabs_voices_response(voice_map)


@router.get("/v1/models")
def list_models(request: Request):
    check_auth(request)
    return {
        "models": [
            {"model_id": "eleven_multilingual_v2", "name": "Eleven Multilingual v2 (compat)"},
            {"model_id": "eleven_turbo_v2", "name": "Eleven Turbo v2 (compat)"},
        ]
    }


@router.post("/v1/text-to-speech/{voice_id}")
@router.post("/v1/text-to-speech/{voice_id}/stream")
def create_speech_elevenlabs(voice_id: str, payload: ElevenLabsSpeechRequest, request: Request):
    check_auth(request)

    settings = request.app.state.settings
    engine = request.app.state.engine
    cache = request.app.state.cache
    tts_service = request.app.state.tts_service

    voice_map = get_elevenlabs_voice_map(settings.elevenlabs_voice_map_json)
    silero_speaker = map_voice_id_to_silero(
        voice_id=voice_id,
        default_speaker=engine.default_speaker,
        voice_map=voice_map,
    )

    if settings.show_text or settings.force_play:
        log.info("[ElevenLabs] Text: %s", payload.text.strip())

    out_fmt = elevenlabs_output_to_internal_format(payload.output_format)

    key_src = (
        f"provider=elevenlabs|lar={settings.language_aware_routing}|voice_id={voice_id}|"
        f"voice={silero_speaker}|fmt={out_fmt}|sr={engine.sample_rate}|text={payload.text.strip()}"
    )
    key = hashlib.sha256(key_src.encode("utf-8")).hexdigest()

    cached = cache.get(key)
    if cached is not None:
        return StreamingResponse(BytesIO(cached), media_type=media_type_for(out_fmt))

    wav_bytes = tts_service.synthesize(payload.text, silero_speaker)
    out_bytes = encode_audio(
        wav_bytes=wav_bytes,
        out_format=out_fmt,
        ffmpeg_bin=settings.ffmpeg_bin,
        speed=1.0,
    )

    cache.put(key, out_bytes)
    return StreamingResponse(BytesIO(out_bytes), media_type=media_type_for(out_fmt))
