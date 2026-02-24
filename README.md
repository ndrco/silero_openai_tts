# Silero OpenAI-Compatible TTS

A **local**, self-hosted Text-to-Speech (TTS) server that implements the **OpenAI TTS API** (`POST /v1/audio/speech`).

The primary goal of this project is to provide a **drop-in, OpenAI API-compatible TTS backend** for
[OpenClaw](https://github.com/openclaw/openclaw) — so OpenClaw can speak without relying on external cloud services.
That said, this server works with **any** project that expects an OpenAI-compatible TTS endpoint: just point the
client to this server’s base URL.

Under the hood it uses **Silero TTS** models via `torch.hub` (downloaded on first run), plus a small text
normalization pipeline focused on **Russian and English**, including **numeral expansion**.

## What is this project for?

The project's key advantage is very fast CPU-based voice-over. In practice, this allows scarce GPU resources to be reserved for local LLM, while TTS can be run separately on the CPU with low latency.

The project also implements voice-over autoplay directly on the server. This mode is especially useful because the current version of OpenClaw's built-in client-side autoplay (in the webchat browser) is unstable.

---

## Features

- **OpenAI API compatible**: implements `POST /v1/audio/speech` with familiar request fields:
  `model`, `input`, `voice`, `response_format`, `speed`.
- **ElevenLabs-compatible mode (optional)**: can expose `POST /v1/text-to-speech/{voice_id}` and `GET /v1/voices` for clients expecting ElevenLabs-style API.
- **Designed for OpenClaw**, but works with any OpenAI-compatible client.
- **Russian + English support** (automatic recognition).
- **Reads numerals naturally**:
  - expands integers into words;
  - for Russian, adjusts noun forms to agree with numbers (e.g. “21 рубль / 22 рубля / 25 рублей”);
  - expands common patterns like `%` and `₽` (ruble symbol).
- **Multiple voices**:
  - accepts OpenAI voice names (`alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer`) and maps them to Silero speakers;
  - also accepts Silero speaker IDs directly (e.g. `baya`, `aidar`, `kseniya`, `xenia`, `eugene`, `random`).
- **Multiple output formats**: `wav`, `mp3`, `opus`, `aac`, `flac`.
- **Speed control** (`0.25`–`4.0`) using FFmpeg audio filters.
- **Disk cache** to avoid regenerating the same phrase repeatedly.
- **Optional API key** (Bearer token) for private deployments.
- **Runs on CPU by default**, with optional GPU (CUDA) support if your PyTorch build supports it.

---

## Quickstart

### 0) Clone the repository

```bash
git clone https://github.com/ndrco/silero_openai_tts.git
cd silero_openai_tts
```

### 1) System dependencies

You need **FFmpeg** (for encoding and speed control) and **libsndfile** (for WAV I/O).

**Debian / Ubuntu (incl. WSL2):**
```bash
sudo apt update
sudo apt install -y ffmpeg libsndfile1
```

**Windows (PowerShell):**

1. Install Python 3.10+ from the official website and make sure `python` is available in `PATH`.
2. Install FFmpeg (required for non-WAV formats and speed control), for example via winget:

```powershell
winget install Gyan.FFmpeg
```

3. Verify installation:

```powershell
python --version
ffmpeg -version
```

### 2) Python environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

**Windows (PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e .
```

If PowerShell blocks script execution, enable local scripts for the current user once:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 3) Configure

Copy `.env.example` to `.env` and edit as needed:

```bash
cp .env.example .env
```

**Windows (PowerShell):**

```powershell
copy .env.example .env
```

### 4) Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Windows (PowerShell):**

```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

If you installed the package with `pip install -e .`, you can also use the console command:

```bash
silero-tts
```

Or run it directly from the virtual environment without activating it first:

```bash
./.venv/bin/silero-tts
```

Windows equivalent:

```powershell
.\.venv\Scripts\silero-tts.exe
```

**CLI options:**

```bash
silero-tts --help
```

| Option | Description |
|--------|-------------|
| `--host` | Host interface to bind (default: `0.0.0.0`) |
| `--port` | Port to listen on (default: `8000`) |
| `--force-play` | Force-enable audio playback on the server side (also enables text output) |
| `--show-text` | Print text to console before synthesis |

**Examples:**

```bash
# Run with force-play enabled (plays audio + shows text)
silero-tts --force-play

# Run with text output only
silero-tts --show-text

# Run with both options on custom port
silero-tts --port 8080 --force-play
```

On first start the server will download the selected Silero model (via `torch.hub`).

---

## API

### Endpoint

`POST /v1/audio/speech`

### Request body (JSON)

| Field | Type | Required | Notes |
|------|------|----------|------|
| `model` | string | yes | OpenAI-compatible field. **Ignored** by this server (kept for compatibility). |
| `input` | string | yes | Text to synthesize (typical limit: 1–4096 chars). |
| `voice` | string | yes | OpenAI voice name or Silero speaker ID. |
| `response_format` | string | no | `wav` (default), `mp3`, `opus`, `aac`, `flac` |
| `speed` | number | no | Playback speed (default `1.0`, range `0.25`–`4.0`) |

### Example (curl)

```bash
curl http://localhost:8000/v1/audio/speech   -H "Content-Type: application/json"   -d '{
    "model": "gpt-4o-mini-tts",
    "voice": "alloy",
    "input": "У меня 5 запросов и 21 рубль.",
    "response_format": "mp3",
    "speed": 1.1
  }'   --output out.mp3
```

### Authentication

If `REQUIRE_AUTH=true`, add:

```bash
-H "Authorization: Bearer YOUR_API_KEY"
```

### Skip playback

To skip the currently playing audio (when `AUTO_PLAY=true`):

```bash
curl -X DELETE http://localhost:8000/v1/audio/speech/skip \
  -H "Authorization: Bearer YOUR_API_KEY"
```

Response:
```json
{"skipped": true}
```

If no audio was playing, returns `{"skipped": false}`.

---


## ElevenLabs-compatible adapter (optional)

You can enable an additional ElevenLabs-style API surface on top of the same Silero backend:

- `GET /v1/voices`
- `GET /v1/models`
- `POST /v1/text-to-speech/{voice_id}`
- `POST /v1/text-to-speech/{voice_id}/stream` (compat alias in this version)

Enable it in `.env`:

```bash
ENABLE_ELEVENLABS_COMPAT=true
ELEVENLABS_REQUIRE_XI_API_KEY=true
```

If `REQUIRE_AUTH=true`, auth works with either:
- `Authorization: Bearer <API_KEY>`
- `xi-api-key: <API_KEY>` (recommended for ElevenLabs-compatible clients)

Example request:

```bash
curl http://localhost:8000/v1/text-to-speech/EXAVITQu4vr4xnSDxMaL \
  -H "xi-api-key: dummy-local-key" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello from ElevenLabs-compatible endpoint",
    "model_id": "eleven_multilingual_v2",
    "output_format": "mp3_44100_128"
  }' \
  --output out.mp3
```

`output_format` mapping in this version:
- `mp3_*` -> MP3 response
- `pcm_*` -> WAV response

You can override voice IDs via `ELEVENLABS_VOICE_MAP_JSON` (JSON object in env).

## OpenClaw integration

OpenClaw expects an OpenAI-compatible TTS endpoint. Run this server locally and configure OpenClaw to use:

- **Base URL**: `http://127.0.0.1:8000` (or wherever you host it)
- **Endpoint**: `/v1/audio/speech`
- **API key**: optional (only if you enable `REQUIRE_AUTH`)

### Recommended OpenClaw config
Add the following to your OpenClaw config (e.g. ~/.openclaw/openclaw.json):

**Required** (so OpenClaw sends TTS requests to this local server and doesn’t need a real key):

```json
"env": {
  "OPENAI_TTS_BASE_URL": "http://127.0.0.1:8000/v1",
  "OPENAI_API_KEY": "dummy-local-key"
}
```

- `OPENAI_TTS_BASE_URL` points OpenClaw to the local OpenAI-compatible API base (note the `/v1` suffix).
- `OPENAI_API_KEY` is a placeholder because many OpenAI-compatible clients expect a key field even for local endpoints; if you enable `REQUIRE_AUTH`, set this to the same token as the server’s `API_KEY`.

**Nice to have** (auto-speak + default voice, with Edge TTS disabled):

```json
"messages": {
  "ackReactionScope": "group-mentions",
  "tts": {
    "provider": "openai",
    "auto": "always",
    "mode": "final",
    "openai": { "voice": "alloy" },
    "edge": { "enabled": false }
  }
}
```

Result: OpenClaw gets local speech synthesis with lower latency and no external calls.

---

## Configuration

Configuration is done via environment variables (loaded from `.env`).

### Networking

- `HOST` (default: `0.0.0.0`) — interface to bind. Use `127.0.0.1` to restrict access to local machine only.
- `PORT` (default: `8000`) — port to listen on.

### Silero model

- `SILERO_LANGUAGE` (default: `ru`) — language code (e.g. `ru`, `en`).
- `SILERO_MODEL_ID` (default: `v5_1_ru`) — Silero model ID for the selected language (e.g. `v5_ru`, `v4_ru`).
- `SILERO_SAMPLE_RATE` (default: `48000`) — output sample rate in Hz (typical values: `8000`, `24000`, `48000`).
- `SILERO_DEVICE` (default: `cpu`) — `cpu` or `cuda`.
- `SILERO_NUM_THREADS` (default: `0`) — inference threads (`0` = auto).
- `SILERO_DEFAULT_SPEAKER` (default: `kseniya`) — speaker used when `voice` is unknown/unmapped.
- `SILERO_MODELS_DIR` (default: `models`) — directory for downloaded models (if your implementation persists them).

### Authentication

- `REQUIRE_AUTH` (default: `false`) — if `true`, requests must include `Authorization: Bearer ...`.
- `API_KEY` (default: `dummy-local-key`) — expected Bearer token.

### Cache

- `CACHE_DIR` (default: `.cache_tts`) — directory where synthesized audio is cached.
- `CACHE_MAX_FILES` (default: `2000`) — maximum number of cached files (oldest are deleted when exceeded).

### Audio encoding

- `FFMPEG_BIN` (default: `ffmpeg`) — path to FFmpeg binary.
- `FFPLAY_BIN` (default: `ffplay`) — path to FFplay binary (used for auto-play).
- `AUTO_PLAY` (default: `false`) — if `true`, synthesized audio is automatically played through the server's default audio output device. Requires `ffplay` (included with ffmpeg).

## Additional options
- `AUTO_PLAY_SHOW_SKIP_WINDOW` (default: `true`) — if `true`, a local Tkinter window with the **Skip** button is shown while server playback is active; the button is hidden when playback finishes.
- `FORCE_PLAY` (default: `false`) — force-enable audio playback on the server side (CLI override). When enabled, also prints text to console before synthesis.
- `SHOW_TEXT` (default: `false`) — print text to console before synthesis (CLI override).

---

## Voice mapping

The server accepts **OpenAI voice names** and maps them to Silero speakers. Example mapping:

| OpenAI voice | Silero speaker (example) |
|---|---|
| `alloy` | `baya` |
| `echo` | `aidar` |
| `fable` | `kseniya` |
| `onyx` | `eugene` |
| `nova` | `xenia` |
| `shimmer` | `baya` |

You may also pass a Silero speaker directly (e.g. `aidar`, `baya`, `kseniya`, `xenia`, `eugene`, `random`).

---

## Text normalization (numbers, currencies, etc.)

Before synthesis, input text goes through a small normalizer that:

- expands integers (e.g. `5` → `five` / `пять`);
- expands patterns like `10%` and `21 ₽`;
- in Russian, inflects nearby nouns to match the number (more natural grammar).

If you need more rules (dates, times, abbreviations), extend the normalization step.

---

## Troubleshooting

- **MP3/OPUS/AAC/FLAC output fails**: ensure `ffmpeg` is installed and `FFMPEG_BIN` points to it.
- **CUDA not used**: make sure your PyTorch build supports CUDA and `SILERO_DEVICE=cuda`.
- **First run is slow**: the model is downloaded the first time. Subsequent starts are faster.
- **No sound / broken audio**: try `response_format: "wav"` first to isolate encoding issues.

---

## License

This project is released under the **MIT License** (a permissive “free” license).
Silero models themselves have their own licensing terms — please check the upstream Silero repository for details.

---

## Acknowledgements

- [Silero Models](https://github.com/snakers4/silero-models) — the underlying TTS models.
- [OpenClaw](https://github.com/openclaw/openclaw) — the chatbot project this server was built to support.
