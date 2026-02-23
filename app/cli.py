# app/cli.py
import argparse
import os
import uvicorn


def main():
    parser = argparse.ArgumentParser(description="Silero OpenAI-compatible TTS server")
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host interface to bind (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to listen on (default: 8000)",
    )
    parser.add_argument(
        "--force-play",
        action="store_true",
        help="Force-enable audio playback on the server side",
    )
    parser.add_argument(
        "--show-text",
        action="store_true",
        help="Print text to console before synthesis",
    )
    args = parser.parse_args()

    # Apply CLI overrides via environment variables
    if args.force_play:
        os.environ["FORCE_PLAY"] = "true"
    if args.show_text:
        os.environ["SHOW_TEXT"] = "true"

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=False,
    )