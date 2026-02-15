import subprocess
from typing import Literal

AudioFormat = Literal["wav", "mp3", "opus", "aac", "flac"]

MEDIA_TYPES = {
    "wav": "audio/wav",
    "mp3": "audio/mpeg",
    "opus": "audio/ogg",
    "aac": "audio/aac",
    "flac": "audio/flac",
}

def media_type_for(fmt: AudioFormat) -> str:
    return MEDIA_TYPES.get(fmt, "application/octet-stream")

def _atempo_chain(speed: float) -> str:
    if speed <= 0:
        speed = 1.0
    filters = []
    s = float(speed)
    while s > 2.0:
        filters.append("atempo=2.0")
        s /= 2.0
    while s < 0.5:
        filters.append("atempo=0.5")
        s /= 0.5
    filters.append(f"atempo={s:.6f}")
    return ",".join(filters)

def encode_audio(wav_bytes: bytes, out_format: AudioFormat, ffmpeg_bin: str, speed: float = 1.0) -> bytes:
    if out_format == "wav" and abs(speed - 1.0) < 1e-6:
        return wav_bytes

    afilter = _atempo_chain(speed) if abs(speed - 1.0) > 1e-6 else None

    if out_format == "wav":
        # wav с изменением скорости через ffmpeg
        args = [ffmpeg_bin, "-hide_banner", "-loglevel", "error", "-i", "pipe:0"]
        if afilter:
            args += ["-filter:a", afilter]
        args += ["-f", "wav", "pipe:1"]
    elif out_format == "mp3":
        args = [ffmpeg_bin, "-hide_banner", "-loglevel", "error", "-i", "pipe:0"]
        if afilter:
            args += ["-filter:a", afilter]
        args += ["-f", "mp3", "pipe:1"]

    elif out_format == "flac":
        args = [ffmpeg_bin, "-hide_banner", "-loglevel", "error", "-i", "pipe:0"]
        if afilter:
            args += ["-filter:a", afilter]
        args += ["-f", "flac", "pipe:1"]

    elif out_format == "aac":
        args = [ffmpeg_bin, "-hide_banner", "-loglevel", "error", "-i", "pipe:0"]
        if afilter:
            args += ["-filter:a", afilter]
        args += ["-c:a", "aac", "-f", "adts", "pipe:1"]

    elif out_format == "opus":
        args = [ffmpeg_bin, "-hide_banner", "-loglevel", "error", "-i", "pipe:0"]
        if afilter:
            args += ["-filter:a", afilter]
        args += ["-c:a", "libopus", "-f", "ogg", "pipe:1"]

    else:
        raise ValueError(f"Unsupported format: {out_format}")

    proc = subprocess.run(args, input=wav_bytes, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", errors="ignore")[:4000]
        raise RuntimeError(f"ffmpeg failed: {err}")
    return proc.stdout
