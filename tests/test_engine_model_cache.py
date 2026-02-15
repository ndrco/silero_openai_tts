"""Tests for caching Silero models in a local directory."""
import os
import sys
import types

from app.tts.engine import SileroTTSEngine


class _FakeModel:
    def to(self, _device):
        return self


class _FakeTorch:
    def __init__(self):
        self.cuda = types.SimpleNamespace(
            is_available=lambda: False,
            get_device_name=lambda _i: "Fake GPU",
        )
        self.version = types.SimpleNamespace(cuda="0.0")
        self.hub = types.SimpleNamespace(load=self._hub_load)
        self.inference_mode = _FakeInferenceMode

    def set_num_threads(self, _threads: int):
        return None

    def device(self, name: str):
        return types.SimpleNamespace(type=name)

    @staticmethod
    def _hub_load(**_kwargs):
        return (_FakeModel(), ["a", "b"], 48000, "example", lambda **_k: [])


class _FakeInferenceMode:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_engine_sets_torch_home_to_models_dir(tmp_path, monkeypatch):
    """When loading the engine, TORCH_HOME points to the project models directory."""
    fake_torch = _FakeTorch()
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    models_dir = tmp_path / "models"
    engine = SileroTTSEngine(
        language="ru",
        model_id="v5_1_ru",
        device="cpu",
        sample_rate=48000,
        default_speaker="baya",
        models_dir=str(models_dir),
    )

    engine.load()

    assert models_dir.exists()
    assert os.environ["TORCH_HOME"] == str(models_dir.resolve())
