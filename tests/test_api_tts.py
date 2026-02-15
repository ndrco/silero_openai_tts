"""TTS API tests: POST /v1/audio/speech."""
import pytest
from fastapi.testclient import TestClient


def test_speech_success(client: TestClient, valid_speech_payload: dict) -> None:
    """A successful request returns 200 and audio in WAV format."""
    response = client.post("/v1/audio/speech", json=valid_speech_payload)
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert len(response.content) > 0
    # Minimal WAV: 44-byte header + data
    assert response.content[:4] == b"RIFF"


def test_speech_success_cached(client: TestClient, valid_speech_payload: dict) -> None:
    """The same repeated request returns a cached response."""
    r1 = client.post("/v1/audio/speech", json=valid_speech_payload)
    r2 = client.post("/v1/audio/speech", json=valid_speech_payload)
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.content == r2.content


def test_speech_validation_missing_input(client: TestClient) -> None:
    """Missing input returns 422."""
    payload = {"model": "gpt-4o-mini-tts", "voice": "alloy"}
    response = client.post("/v1/audio/speech", json=payload)
    assert response.status_code == 422


def test_speech_validation_missing_model(client: TestClient) -> None:
    """Missing model returns 422."""
    payload = {"voice": "alloy", "input": "Текст"}
    response = client.post("/v1/audio/speech", json=payload)
    assert response.status_code == 422


def test_speech_validation_missing_voice(client: TestClient) -> None:
    """Missing voice returns 422."""
    payload = {"model": "gpt-4o-mini-tts", "input": "Текст"}
    response = client.post("/v1/audio/speech", json=payload)
    assert response.status_code == 422


def test_speech_validation_empty_input(client: TestClient) -> None:
    """Empty input returns 422."""
    payload = {
        "model": "gpt-4o-mini-tts",
        "voice": "alloy",
        "input": "",
    }
    response = client.post("/v1/audio/speech", json=payload)
    assert response.status_code == 422


def test_speech_validation_speed_too_low(client: TestClient, valid_speech_payload: dict) -> None:
    """speed < 0.25 returns 422."""
    valid_speech_payload["speed"] = 0.2
    response = client.post("/v1/audio/speech", json=valid_speech_payload)
    assert response.status_code == 422


def test_speech_validation_speed_too_high(client: TestClient, valid_speech_payload: dict) -> None:
    """speed > 4.0 returns 422."""
    valid_speech_payload["speed"] = 5.0
    response = client.post("/v1/audio/speech", json=valid_speech_payload)
    assert response.status_code == 422


def test_speech_auth_no_header_returns_401(client_with_auth: TestClient, valid_speech_payload: dict) -> None:
    """Without auth when require_auth=True, returns 401."""
    response = client_with_auth.post("/v1/audio/speech", json=valid_speech_payload)
    assert response.status_code == 401
    assert "detail" in response.json()


def test_speech_auth_wrong_token_returns_401(client_with_auth: TestClient, valid_speech_payload: dict) -> None:
    """Invalid Bearer token returns 401."""
    response = client_with_auth.post(
        "/v1/audio/speech",
        json=valid_speech_payload,
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert response.status_code == 401


def test_speech_auth_valid_token_returns_200(
    client_with_auth: TestClient, valid_speech_payload: dict
) -> None:
    """With a valid Bearer token, the request succeeds."""
    response = client_with_auth.post(
        "/v1/audio/speech",
        json=valid_speech_payload,
        headers={"Authorization": "Bearer test-secret-key"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert len(response.content) > 0


def test_speech_different_voices(client: TestClient, valid_speech_payload: dict) -> None:
    """Different voices return responses (OpenAI -> Silero mapping check)."""
    for voice in ("alloy", "baya", "eugene"):
        payload = {**valid_speech_payload, "voice": voice}
        response = client.post("/v1/audio/speech", json=payload)
        assert response.status_code == 200, f"voice={voice}"
        assert len(response.content) > 0


def test_speech_response_format_wav(client: TestClient, valid_speech_payload: dict) -> None:
    """Explicit response_format=wav returns audio/wav."""
    valid_speech_payload["response_format"] = "wav"
    response = client.post("/v1/audio/speech", json=valid_speech_payload)
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"


def test_speech_with_latin_text_succeeds(client: TestClient, valid_speech_payload: dict) -> None:
    """Text with Latin script (English words) does not break the request — transliterated to Cyrillic."""
    valid_speech_payload["input"] = "Привет, hello и API."
    response = client.post("/v1/audio/speech", json=valid_speech_payload)
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert len(response.content) > 0


def test_speech_with_language_aware_routing_uses_both_engines(
    client_with_routing: TestClient, app_with_routing, valid_speech_payload: dict
) -> None:
    """In mixed RU/EN text, segments are synthesized by different engines and concatenated."""
    payload = {**valid_speech_payload, "input": "Привет, hello world! Пока."}
    response = client_with_routing.post("/v1/audio/speech", json=payload)
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert response.content[:4] == b"RIFF"

    ru_calls = app_with_routing.state.engine.calls
    en_calls = app_with_routing.state.en_engine.calls

    assert len(ru_calls) == 2
    assert len(en_calls) == 1
    assert "Привет" in ru_calls[0][0]
    assert "hello" in en_calls[0][0].lower()
