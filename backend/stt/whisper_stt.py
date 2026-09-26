import os
from faster_whisper import WhisperModel
import logging
from config import config
from utils.audio_utils import save_temp_audio, delete_temp_file

logger = logging.getLogger(__name__)

class WhisperSTT:
    def __init__(self):
        self.model_size = config.whisper_model_size
        self.device = config.whisper_device
        self.compute_type = config.whisper_compute_type
        self.model = None

    def set_model_size(self, model_size: str):
        model_size = model_size.strip()
        allowed_sizes = {"tiny", "base", "small", "medium", "large-v3", "large-v3-turbo"}
        if model_size not in allowed_sizes:
            raise ValueError(f"Whisper model size must be one of: {', '.join(sorted(allowed_sizes))}")
        if model_size != self.model_size:
            self.model = None
            self.model_size = model_size
            config.whisper_model_size = model_size

    def _load_model(self):
        if self.model is None:
            logger.info(f"Loading Whisper model {self.model_size} on {self.device}...")
            self.model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
            logger.info("Whisper model loaded.")

    def transcribe(self, audio_bytes: bytes) -> str:
        temp_file = save_temp_audio(audio_bytes)
        try:
            self._load_model()
            segments, info = self.model.transcribe(
                temp_file,
                vad_filter=True,
                language="ja"
            )
            text = "".join([segment.text for segment in segments])
            return text.strip()
        except Exception as e:
            logger.error(f"Error during transcription: {e}")
            return ""
        finally:
            delete_temp_file(temp_file)
