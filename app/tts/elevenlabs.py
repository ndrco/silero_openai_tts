import json
from typing import Any

DEFAULT_ELEVENLABS_VOICE_MAP = {
    "EXAVITQu4vr4xnSDxMaL": {"name": "Rachel-compat", "speaker": "baya"},
    "VR6AewLTigWG4xSOukaG": {"name": "Arnold-compat", "speaker": "aidar"},
    "TxGEqnHWrfWFTfGW9XjX": {"name": "Josh-compat", "speaker": "eugene"},
    "pNInz6obpgDQGcFmaJgB": {"name": "Adam-compat", "speaker": "xenia"},
    "MF3mGyEYCl7XYWbV9V6O": {"name": "Elli-compat", "speaker": "kseniya"},
    "random": {"name": "Random-compat", "speaker": "random"},
}


def get_elevenlabs_voice_map(raw_json: str | None) -> dict[str, dict[str, str]]:
    if not raw_json:
        return DEFAULT_ELEVENLABS_VOICE_MAP

    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError:
        return DEFAULT_ELEVENLABS_VOICE_MAP

    if not isinstance(parsed, dict):
        return DEFAULT_ELEVENLABS_VOICE_MAP

    result: dict[str, dict[str, str]] = {}
    for voice_id, payload in parsed.items():
        if not isinstance(voice_id, str) or not isinstance(payload, dict):
            continue
        speaker = payload.get("speaker")
        if not isinstance(speaker, str) or not speaker.strip():
            continue
        name = payload.get("name")
        if not isinstance(name, str) or not name.strip():
            name = voice_id
        result[voice_id] = {"name": name.strip(), "speaker": speaker.strip()}

    return result or DEFAULT_ELEVENLABS_VOICE_MAP


def map_voice_id_to_silero(voice_id: str, default_speaker: str, voice_map: dict[str, dict[str, str]]) -> str:
    voice_id = (voice_id or "").strip()
    if not voice_id or voice_id == "default":
        return default_speaker

    mapped = voice_map.get(voice_id)
    if mapped:
        return mapped["speaker"]

    return default_speaker


def elevenlabs_output_to_internal_format(output_format: str | None) -> str:
    value = (output_format or "mp3_44100_128").strip().lower()
    if value.startswith("mp3"):
        return "mp3"
    if value.startswith("pcm"):
        return "wav"
    return "mp3"


def elevenlabs_voices_response(voice_map: dict[str, dict[str, str]]) -> dict[str, Any]:
    voices = []
    for voice_id, payload in voice_map.items():
        voices.append(
            {
                "voice_id": voice_id,
                "name": payload["name"],
                "labels": {"provider": "silero", "speaker": payload["speaker"]},
                "preview_url": None,
            }
        )
    return {"voices": voices}
