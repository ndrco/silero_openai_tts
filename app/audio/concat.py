import io
import numpy as np
import soundfile as sf


def concat_wav_bytes(parts: list[bytes], expected_sample_rate: int) -> bytes:
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

    merged = np.concatenate(decoded_parts, axis=0)
    out = io.BytesIO()
    sf.write(out, merged, expected_sample_rate, format="WAV", subtype="PCM_16")
    return out.getvalue()
