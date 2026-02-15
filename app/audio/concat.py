import io
import numpy as np
import soundfile as sf


def concat_wav_bytes(parts: list[bytes], expected_sample_rate: int, pause_sec: float = 0.0) -> bytes:
    if not parts:
        return b""

    decoded_parts: list[np.ndarray] = []
    for wav_bytes in parts:
        audio_np, sample_rate = sf.read(io.BytesIO(wav_bytes), dtype="float32")
        if sample_rate != expected_sample_rate:
            raise RuntimeError(
                f"Sample rate mismatch while concatenating audio: got {sample_rate}, expected {expected_sample_rate}"
            )
        if isinstance(audio_np, np.ndarray) and audio_np.ndim > 1:
            audio_np = audio_np[:, 0]
        decoded_parts.append(audio_np.astype(np.float32))

    if len(decoded_parts) > 1 and pause_sec > 0:
        silence = np.zeros(int(expected_sample_rate * pause_sec), dtype=np.float32)
        to_merge = []
        for i, p in enumerate(decoded_parts):
            to_merge.append(p)
            if i < len(decoded_parts) - 1:
                to_merge.append(silence)
        merged = np.concatenate(to_merge, axis=0)
    else:
        merged = np.concatenate(decoded_parts, axis=0)
    out = io.BytesIO()
    sf.write(out, merged, expected_sample_rate, format="WAV", subtype="PCM_16")
    return out.getvalue()
