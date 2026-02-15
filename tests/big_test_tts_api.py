#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import wave
from pathlib import Path

import requests


URL = os.environ.get("TTS_URL", "http://localhost:8000/v1/audio/speech")
OUT_DIR = Path(os.environ.get("TTS_OUT_DIR", "out"))
OUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL = os.environ.get("TTS_MODEL", "gpt-4o-mini-tts")
VOICE = os.environ.get("TTS_VOICE", "alloy")
SPEED = float(os.environ.get("TTS_SPEED", "1.0"))

# Длинный текст: много предложений + числа + проценты + рубли + разные формы.
# Цель: проверить, что сервис не "обрезает хвост", и что нормализация чисел работает.
LONG_TEXT = (
    "Проверка длинной озвучки. Сейчас я специально произнесу длинный абзац, "
    "чтобы убедиться, что звук не обрезается в конце и что сервер корректно "
    "возвращает аудиофайл целиком. У меня есть 1 рубль, потом 2 рубля, потом 5 рублей, "
    "а ещё 21 рубль и 101 рубль — да, числа здесь не случайны. "
    "Дальше добавим проценты: 1%, 2%, 5% и 21%, чтобы проверить согласование. "
    "Теперь немного технических деталей: мы запускаем локальный сервис, имитирующий OpenAI API. "
    "Пусть фраза будет длинной: я повторю мысль иначе — этот текст нужен, чтобы проверить, "
    "не теряются ли последние слова, не возникает ли пауза с обрывом и не ломается ли кодирование. "
    "Продолжаю: если ты слышишь это предложение, значит поток не обрывается слишком рано. "
    "Ещё один кусок текста для надёжности. "
    "В конце я добавлю контрольную строку: КОНТРОЛЬНАЯ ФРАЗА В САМОМ КОНЦЕ, НЕ ДОЛЖНА ПРОПАСТЬ."
)

def post_tts(response_format: str, text: str) -> requests.Response:
    payload = {
        "model": MODEL,
        "voice": VOICE,
        "input": text,
        "response_format": response_format,
        "speed": SPEED,
    }
    t0 = time.time()
    r = requests.post(URL, json=payload, timeout=180)
    dt = time.time() - t0
    print(f"\n=== {response_format.upper()} request ===")
    print("POST", URL)
    print("status:", r.status_code, "time_sec:", f"{dt:.2f}")
    print("content-type:", r.headers.get("content-type"))
    if r.status_code != 200:
        print("error body (first 500 chars):")
        print(r.text[:500])
    return r

def save_bytes(path: Path, data: bytes) -> None:
    path.write_bytes(data)
    print("saved:", path, "size_bytes:", len(data))

def wav_duration_seconds(path: Path) -> float | None:
    try:
        with wave.open(str(path), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            if rate <= 0:
                return None
            return frames / float(rate)
    except Exception:
        return None

def ffprobe_duration_seconds(path: Path) -> float | None:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None
    try:
        # Выводим duration в секундах
        cmd = [
            ffprobe, "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json",
            str(path)
        ]
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if p.returncode != 0:
            return None
        j = json.loads(p.stdout)
        dur = j.get("format", {}).get("duration")
        return float(dur) if dur is not None else None
    except Exception:
        return None

def main() -> int:
    print("TTS_URL:", URL)
    print("MODEL:", MODEL, "VOICE:", VOICE, "SPEED:", SPEED)
    print("out dir:", OUT_DIR.resolve())

    # WAV
    r_wav = post_tts("wav", LONG_TEXT)
    if r_wav.status_code != 200:
        return 2
    wav_path = OUT_DIR / "test_long.wav"
    save_bytes(wav_path, r_wav.content)

    dur_wav = wav_duration_seconds(wav_path)
    if dur_wav is not None:
        print("wav duration_sec:", f"{dur_wav:.2f}")
        if dur_wav < 5.0:
            print("WARNING: WAV seems too short (<5s). Possible truncation or TTS failure.")
    else:
        print("wav duration_sec: (could not parse)")

    # MP3
    r_mp3 = post_tts("mp3", LONG_TEXT)
    if r_mp3.status_code != 200:
        return 3
    mp3_path = OUT_DIR / "test_long.mp3"
    save_bytes(mp3_path, r_mp3.content)

    dur_mp3 = ffprobe_duration_seconds(mp3_path)
    if dur_mp3 is not None:
        print("mp3 duration_sec:", f"{dur_mp3:.2f}")
        if dur_mp3 < 5.0:
            print("WARNING: MP3 seems too short (<5s). Possible truncation or encoding failure.")
    else:
        print("mp3 duration_sec: (ffprobe not found or parse failed)")
        print("Tip: install ffmpeg to get ffprobe, e.g. sudo apt-get install -y ffmpeg")

    # Простая эвристика "обрезки": если mp3 длительность сильно меньше wav (или сильно меньше ожидаемой)
    if dur_wav is not None and dur_mp3 is not None:
        ratio = dur_mp3 / dur_wav if dur_wav > 0 else 0
        print("duration ratio mp3/wav:", f"{ratio:.3f}")
        if ratio < 0.85:
            print("WARNING: MP3 duration noticeably smaller than WAV. Possible truncation/encode issue.")

    print("\n✅ Done. Listen to files in ./out/:")
    print("   ", wav_path)
    print("   ", mp3_path)
    print("If you want a quick listen in WSL: ffplay out/test_long.wav  (requires ffmpeg)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
