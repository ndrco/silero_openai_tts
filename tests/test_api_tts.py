"""Тесты API TTS: POST /v1/audio/speech."""
import pytest
from fastapi.testclient import TestClient


def test_speech_success(client: TestClient, valid_speech_payload: dict) -> None:
    """Успешный запрос возвращает 200 и аудио в формате WAV."""
    response = client.post("/v1/audio/speech", json=valid_speech_payload)
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert len(response.content) > 0
    # Минимальный WAV: заголовок 44 байта + данные
    assert response.content[:4] == b"RIFF"


def test_speech_success_cached(client: TestClient, valid_speech_payload: dict) -> None:
    """Повторный тот же запрос отдаёт закэшированный ответ."""
    r1 = client.post("/v1/audio/speech", json=valid_speech_payload)
    r2 = client.post("/v1/audio/speech", json=valid_speech_payload)
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.content == r2.content


def test_speech_validation_missing_input(client: TestClient) -> None:
    """Отсутствие input даёт 422."""
    payload = {"model": "gpt-4o-mini-tts", "voice": "alloy"}
    response = client.post("/v1/audio/speech", json=payload)
    assert response.status_code == 422


def test_speech_validation_missing_model(client: TestClient) -> None:
    """Отсутствие model даёт 422."""
    payload = {"voice": "alloy", "input": "Текст"}
    response = client.post("/v1/audio/speech", json=payload)
    assert response.status_code == 422


def test_speech_validation_missing_voice(client: TestClient) -> None:
    """Отсутствие voice даёт 422."""
    payload = {"model": "gpt-4o-mini-tts", "input": "Текст"}
    response = client.post("/v1/audio/speech", json=payload)
    assert response.status_code == 422


def test_speech_validation_empty_input(client: TestClient) -> None:
    """Пустой input даёт 422."""
    payload = {
        "model": "gpt-4o-mini-tts",
        "voice": "alloy",
        "input": "",
    }
    response = client.post("/v1/audio/speech", json=payload)
    assert response.status_code == 422


def test_speech_validation_speed_too_low(client: TestClient, valid_speech_payload: dict) -> None:
    """speed < 0.25 даёт 422."""
    valid_speech_payload["speed"] = 0.2
    response = client.post("/v1/audio/speech", json=valid_speech_payload)
    assert response.status_code == 422


def test_speech_validation_speed_too_high(client: TestClient, valid_speech_payload: dict) -> None:
    """speed > 4.0 даёт 422."""
    valid_speech_payload["speed"] = 5.0
    response = client.post("/v1/audio/speech", json=valid_speech_payload)
    assert response.status_code == 422


def test_speech_auth_no_header_returns_401(client_with_auth: TestClient, valid_speech_payload: dict) -> None:
    """Без авторизации при require_auth=True возвращается 401."""
    response = client_with_auth.post("/v1/audio/speech", json=valid_speech_payload)
    assert response.status_code == 401
    assert "detail" in response.json()


def test_speech_auth_wrong_token_returns_401(client_with_auth: TestClient, valid_speech_payload: dict) -> None:
    """Неверный Bearer token возвращает 401."""
    response = client_with_auth.post(
        "/v1/audio/speech",
        json=valid_speech_payload,
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert response.status_code == 401


def test_speech_auth_valid_token_returns_200(
    client_with_auth: TestClient, valid_speech_payload: dict
) -> None:
    """С правильным Bearer token запрос успешен."""
    response = client_with_auth.post(
        "/v1/audio/speech",
        json=valid_speech_payload,
        headers={"Authorization": "Bearer test-secret-key"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert len(response.content) > 0


def test_speech_different_voices(client: TestClient, valid_speech_payload: dict) -> None:
    """Разные voice дают ответ (проверка маппинга OpenAI -> Silero)."""
    for voice in ("alloy", "baya", "eugene"):
        payload = {**valid_speech_payload, "voice": voice}
        response = client.post("/v1/audio/speech", json=payload)
        assert response.status_code == 200, f"voice={voice}"
        assert len(response.content) > 0


def test_speech_response_format_wav(client: TestClient, valid_speech_payload: dict) -> None:
    """Явный response_format=wav возвращает audio/wav."""
    valid_speech_payload["response_format"] = "wav"
    response = client.post("/v1/audio/speech", json=valid_speech_payload)
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
