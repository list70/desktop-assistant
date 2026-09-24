import os
import subprocess
from dataclasses import dataclass, field


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
    ollama_endpoint: str = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434")
    llm_model: str = os.getenv("LLM_MODEL", "qwen2.5:7b")
    whisper_model_size: str = os.getenv("WHISPER_MODEL_SIZE", "small")
    whisper_device: str = field(default_factory=_detect_device)
    whisper_compute_type: str = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
    tts_voice: str = os.getenv("TTS_VOICE", "jf_alpha")
    tts_language: str = os.getenv("TTS_LANGUAGE", "j")
    server_host: str = os.getenv("SERVER_HOST", "0.0.0.0")
    server_port: int = int(os.getenv("SERVER_PORT", "8765"))
    audio_sample_rate: int = int(os.getenv("AUDIO_SAMPLE_RATE", "16000"))


config = Config()
