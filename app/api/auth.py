from fastapi import HTTPException, Request


def check_auth(req: Request) -> None:
    """Validate auth using Bearer token and optional xi-api-key header."""
    settings = req.app.state.settings
    if not settings.require_auth:
        return

    auth = req.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        token = auth.split(" ", 1)[1].strip()
        if token == settings.api_key:
            return

    if getattr(settings, "elevenlabs_require_xi_api_key", True):
        xi_api_key = req.headers.get("xi-api-key", "").strip()
        if xi_api_key and xi_api_key == settings.api_key:
            return

    raise HTTPException(status_code=401, detail="Missing or invalid API key")
