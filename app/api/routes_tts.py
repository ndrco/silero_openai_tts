import logging
import hashlib
from io import BytesIO
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from app.api.schemas import SpeechRequest
from app.text.normalize import replace_urls
from app.tts.voices import map_voice_to_silero
from app.audio.concat import concat_wav_bytes
from app.audio.encode import encode_audio, media_type_for

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


def _synthesize_with_routing(request: Request, text: str, speaker: str) -> bytes:
    ru_engine = request.app.state.engine
    en_engine = request.app.state.en_engine
    ru_normalizer = request.app.state.normalizer
    en_normalizer = request.app.state.en_normalizer
    lang_router = request.app.state.language_router

    # First replace URL with "link" so a phrase like "Link to GitHub: https://..." remains one segment as "Link to link"
    text = replace_urls(text)
    segments = lang_router.split(text)
    if not segments:
        return ru_engine.synthesize_wav_bytes(" ", speaker=speaker)

    wav_parts = []
    for segment in segments:
        if segment.lang == "en" and en_engine is not None:
            normalized = en_normalizer.run(segment.text)
            if not normalized or not normalized.strip():
                normalized = " "
            try:
                wav_parts.append(en_engine.synthesize_wav_bytes(normalized, speaker=en_engine.default_speaker))
            except (ValueError, RuntimeError) as e:
                log.warning("EN model rejected segment, fallback to RU: %s", e)
                normalized_ru = ru_normalizer.run(segment.text)
                wav_parts.append(ru_engine.synthesize_wav_bytes(normalized_ru, speaker=speaker))
        else:
            normalized = ru_normalizer.run(segment.text)
            wav_parts.append(ru_engine.synthesize_wav_bytes(normalized, speaker=speaker))

    pause_sec = getattr(request.app.state.settings, "silero_pause_between_fragments_sec", 0.3)
    return concat_wav_bytes(wav_parts, expected_sample_rate=ru_engine.sample_rate, pause_sec=pause_sec)


@router.post("/v1/audio/speech")
def create_speech(payload: SpeechRequest, request: Request):
    _check_auth(request)

    settings = request.app.state.settings
    engine = request.app.state.engine
    normalizer = request.app.state.normalizer
    cache = request.app.state.cache

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

    if settings.language_aware_routing:
        wav_bytes = _synthesize_with_routing(request, payload.input, silero_speaker)
    else:
        normalized = normalizer.run(payload.input)
        wav_bytes = engine.synthesize_wav_bytes(normalized, speaker=silero_speaker)

    out_bytes = encode_audio(
        wav_bytes=wav_bytes,
        out_format=out_fmt,
        ffmpeg_bin=request.app.state.settings.ffmpeg_bin,
        speed=payload.speed or 1.0,
    )

    cache.put(key, out_bytes)
    return StreamingResponse(BytesIO(out_bytes), media_type=media_type_for(out_fmt))
