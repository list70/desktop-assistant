import os
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


def _settings_path() -> Path:
    if os.getenv("APPDATA"):
        base = Path(os.environ["APPDATA"])
    elif os.getenv("XDG_CONFIG_HOME"):
        base = Path(os.environ["XDG_CONFIG_HOME"])
    else:
        base = Path.home() / ".config"
    return base / "desktop-assistant" / "settings.json"


def _detect_device() -> str:
    """Detect if CUDA is available without importing torch."""
    env_device = os.getenv("WHISPER_DEVICE")
    if env_device:
        return env_device
    try:
        subprocess.run(
            ["nvidia-smi"], capture_output=True, check=True, timeout=5
        )
        return "cuda"
    except Exception:
        return "cpu"


@dataclass
class Config:
    """Application configuration, all fields overridable via env vars."""
    ollama_endpoint: str = os.getenv("OLLAMA_ENDPOINT", "http://127.0.0.1:11434")
    llm_model: str = os.getenv("LLM_MODEL", "qwen2.5:7b")
    whisper_model_size: str = os.getenv("WHISPER_MODEL_SIZE", "small")
    whisper_device: str = field(default_factory=_detect_device)
    whisper_compute_type: str = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
    tts_voice: str = os.getenv("TTS_VOICE", "jf_alpha")
    tts_language: str = os.getenv("TTS_LANGUAGE", "j")
    server_host: str = os.getenv("SERVER_HOST", "127.0.0.1")
    server_port: int = int(os.getenv("SERVER_PORT", "8765"))
    audio_sample_rate: int = int(os.getenv("AUDIO_SAMPLE_RATE", "16000"))

    def __post_init__(self):
        try:
            saved = json.loads(_settings_path().read_text(encoding="utf-8"))
            model = saved.get("llm_model") if isinstance(saved, dict) else None
            endpoint = saved.get("ollama_endpoint") if isinstance(saved, dict) else None
            if not os.getenv("LLM_MODEL") and isinstance(model, str) and model.strip():
                self.llm_model = model.strip()
            if not os.getenv("OLLAMA_ENDPOINT") and isinstance(endpoint, str) and endpoint.strip():
                self.ollama_endpoint = endpoint.strip().rstrip("/")
        except (OSError, json.JSONDecodeError):
            pass

    def save_user_settings(self):
        path = _settings_path()
        settings = {}
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(existing, dict):
                settings.update(existing)
        except (OSError, json.JSONDecodeError):
            pass
        settings.update({
            "llm_model": self.llm_model,
            "ollama_endpoint": self.ollama_endpoint.rstrip("/"),
        })
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = path.with_suffix(".tmp")
        temporary_path.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary_path.replace(path)


config = Config()
