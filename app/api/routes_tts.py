import hashlib
from io import BytesIO
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from app.api.schemas import SpeechRequest
from app.tts.voices import map_voice_to_silero
from app.audio.encode import encode_audio, media_type_for

router = APIRouter()

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

    engine = request.app.state.engine
    normalizer = request.app.state.normalizer
    cache = request.app.state.cache

    normalized = normalizer.run(payload.input)
    silero_speaker = map_voice_to_silero(payload.voice, default=engine.default_speaker)
    out_fmt = payload.response_format or "wav"

    key_src = f"{silero_speaker}|{payload.speed}|{out_fmt}|{engine.sample_rate}|{normalized}"
    key = hashlib.sha256(key_src.encode("utf-8")).hexdigest()

    cached = cache.get(key)
    if cached is not None:
        return StreamingResponse(BytesIO(cached), media_type=media_type_for(out_fmt))

    wav_bytes = engine.synthesize_wav_bytes(normalized, speaker=silero_speaker)

    out_bytes = encode_audio(
        wav_bytes=wav_bytes,
        out_format=out_fmt,
        ffmpeg_bin=request.app.state.settings.ffmpeg_bin,
        speed=payload.speed or 1.0,
    )

    cache.put(key, out_bytes)
    return StreamingResponse(BytesIO(out_bytes), media_type=media_type_for(out_fmt))
