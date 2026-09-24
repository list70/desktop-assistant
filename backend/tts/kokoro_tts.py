"""
Kokoro TTS サービス (拡張版)
============================
Kokoro-82M による日本語音声合成。
AURAボイスプロファイルによる感情対応音声切り替えをサポート。
"""

import io
import base64
import logging
from typing import Optional

import numpy as np
import soundfile as sf

from config import config

logger = logging.getLogger(__name__)


class KokoroTTS:
    """
    Kokoro-82M ベースの音声合成サービス。
    感情に応じたボイス切り替え機能付き。
    """

    def __init__(self):
        self.pipeline = None
        self.voice = config.tts_voice
        self.lang_code = config.tts_language
        self.sample_rate = 24000

        # 感情に応じたボイスマッピング
        self.emotion_voice_map = {
            "happy": "jf_nezumi",       # 活発な声
            "sad": "jf_tebukuro",       # 落ち着いた声
            "surprised": "jf_nezumi",   # 元気な声
            "neutral": self.voice,       # デフォルト
            "thinking": self.voice,      # デフォルト
            "angry": "jf_gongitsune",   # 柔らかめの声（怒りを抑えた表現）
        }

    def _load_pipeline(self):
        """パイプラインを遅延ロード"""
        if self.pipeline is None:
            try:
                from kokoro import KPipeline
                logger.info(
                    f"Loading Kokoro TTS pipeline "
                    f"(lang={self.lang_code}, voice={self.voice})..."
                )
                self.pipeline = KPipeline(lang_code=self.lang_code)
                logger.info("Kokoro pipeline loaded successfully.")
            except ImportError as e:
                logger.error(
                    "Failed to import Kokoro. "
                    "Install with: pip install 'kokoro>=0.9.4' 'misaki[ja]'"
                )
                raise
            except Exception as e:
                logger.error(f"Failed to load Kokoro pipeline: {e}")
                raise

    def _get_voice_for_emotion(self, emotion: Optional[str] = None) -> str:
        """感情に応じたボイスIDを返す"""
        if emotion and emotion in self.emotion_voice_map:
            return self.emotion_voice_map[emotion]
        return self.voice

    def synthesize(
        self,
        text: str,
        emotion: Optional[str] = None,
        speed: float = 1.0
    ) -> bytes:
        """
        テキストを音声(WAV)に変換する。

        Args:
            text: 合成するテキスト
            emotion: 感情タグ (happy, sad, neutral, etc.)
            speed: 再生速度 (1.0 = 通常)

        Returns:
            WAVフォーマットのバイトデータ (空の場合は b"")
        """
        if not text or not text.strip():
            return b""

        self._load_pipeline()

        voice = self._get_voice_for_emotion(emotion)

        try:
            generator = self.pipeline(
                text,
                voice=voice,
                speed=speed,
                split_pattern=r'\n+'
            )

            audio_segments = []
            for gs, ps, audio in generator:
                audio_segments.append(audio)

            if not audio_segments:
                logger.warning("TTS generated no audio segments")
                return b""

            combined_audio = np.concatenate(audio_segments)

            # WAVに変換
            buffer = io.BytesIO()
            sf.write(buffer, combined_audio, self.sample_rate, format='WAV')
            return buffer.getvalue()

        except Exception as e:
            logger.error(f"TTS synthesis error: {e}")
            return b""

    def synthesize_base64(
        self,
        text: str,
        emotion: Optional[str] = None,
        speed: float = 1.0
    ) -> str:
        """テキストを音声に変換し、base64エンコードした文字列で返す"""
        audio_bytes = self.synthesize(text, emotion=emotion, speed=speed)
        if not audio_bytes:
            return ""
        return base64.b64encode(audio_bytes).decode("utf-8")

    def list_available_voices(self) -> dict:
        """利用可能なボイスと感情マッピングを返す"""
        return {
            "default_voice": self.voice,
            "language": self.lang_code,
            "emotion_voices": self.emotion_voice_map,
            "available_voices": [
                {"id": "jf_alpha", "name": "Alpha (Female)", "lang": "ja"},
                {"id": "jf_gongitsune", "name": "Gongitsune (Female)", "lang": "ja"},
                {"id": "jf_nezumi", "name": "Nezumi (Female)", "lang": "ja"},
                {"id": "jf_tebukuro", "name": "Tebukuro (Female)", "lang": "ja"},
                {"id": "jm_kumo", "name": "Kumo (Male)", "lang": "ja"},
            ]
        }
