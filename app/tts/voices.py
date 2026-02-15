OPENAI_TO_SILERO = {
    "alloy": "baya",
    "echo": "aidar",
    "fable": "kseniya",
    "onyx": "eugene",
    "nova": "xenia",
    "shimmer": "baya",
}

KNOWN_SILERO_SPEAKERS = {"aidar", "baya", "kseniya", "xenia", "eugene", "random"}

def map_voice_to_silero(voice: str, default: str = "baya") -> str:
    v = (voice or "").strip().lower()
    if v in KNOWN_SILERO_SPEAKERS:
        return v
    return OPENAI_TO_SILERO.get(v, default)
