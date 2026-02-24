"""ElevenLabs-compatible API tests."""

from fastapi.testclient import TestClient


def test_elevenlabs_speech_success(client_with_elevenlabs: TestClient) -> None:
    payload = {
        "text": "Привет, это ElevenLabs-совместимый запрос.",
        "model_id": "eleven_multilingual_v2",
        "output_format": "mp3_44100_128",
    }
    response = client_with_elevenlabs.post("/v1/text-to-speech/EXAVITQu4vr4xnSDxMaL", json=payload)
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert len(response.content) > 0


def test_elevenlabs_stream_alias_success(client_with_elevenlabs: TestClient) -> None:
    payload = {"text": "Потоковый алиас", "output_format": "pcm_24000"}
    response = client_with_elevenlabs.post("/v1/text-to-speech/default/stream", json=payload)
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert response.content[:4] == b"RIFF"


def test_elevenlabs_list_voices(client_with_elevenlabs: TestClient) -> None:
    response = client_with_elevenlabs.get("/v1/voices")
    assert response.status_code == 200
    data = response.json()
    assert "voices" in data
    assert isinstance(data["voices"], list)
    assert any(v["voice_id"] == "EXAVITQu4vr4xnSDxMaL" for v in data["voices"])


def test_elevenlabs_list_models(client_with_elevenlabs: TestClient) -> None:
    response = client_with_elevenlabs.get("/v1/models")
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert any(m["model_id"] == "eleven_multilingual_v2" for m in data["models"])


def test_elevenlabs_auth_via_xi_api_key(client_with_elevenlabs_auth: TestClient) -> None:
    payload = {"text": "Auth test"}

    unauthorized = client_with_elevenlabs_auth.post("/v1/text-to-speech/default", json=payload)
    assert unauthorized.status_code == 401

    authorized = client_with_elevenlabs_auth.post(
        "/v1/text-to-speech/default",
        json=payload,
        headers={"xi-api-key": "test-secret-key"},
    )
    assert authorized.status_code == 200


def test_elevenlabs_validation_empty_text(client_with_elevenlabs: TestClient) -> None:
    response = client_with_elevenlabs.post(
        "/v1/text-to-speech/default",
        json={"text": ""},
    )
    assert response.status_code == 422
