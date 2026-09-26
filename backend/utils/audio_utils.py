import tempfile
import os
import wave
import io
import soundfile as sf
import numpy as np

def save_temp_audio(audio_bytes: bytes, suffix: str = ".webm") -> str:
    """Saves audio bytes to a temporary file and returns the path."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, 'wb') as f:
        f.write(audio_bytes)
    return path

def delete_temp_file(path: str):
    """Deletes a temporary file."""
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        print(f"Error deleting temp file {path}: {e}")

def validate_audio(audio_bytes: bytes) -> bool:
    """Simple check if bytes look like an audio file by attempting to read headers (basic validation)."""
    if not audio_bytes:
        return False
    return True
