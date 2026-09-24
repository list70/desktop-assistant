"""
AURA ボイス設定モジュール
========================
Kokoro-82M TTS の音声設定と、カスタムボイスモデル（RVC等）との統合を管理する。

利用可能な日本語ボイス (Kokoro-82M):
  - jf_alpha    : 女性（標準）
  - jf_gongitsune : 女性（柔らかめ）
  - jf_nezumi   : 女性（活発）
  - jf_tebukuro : 女性（落ち着いた）
  - jm_kumo     : 男性

カスタムボイスの追加方法:
  1. GPT-SoVITS で音声モデルを学習
  2. 学習済みモデルを voice_models/ に配置
  3. config の custom_voice_model にパスを設定
"""

import os
import io
import logging
import base64
from dataclasses import dataclass, field
from typing import Optional, List, Dict

import numpy as np
import soundfile as sf

logger = logging.getLogger(__name__)


# ============================================================
# ボイスプロファイル定義
# ============================================================

@dataclass
class VoiceProfile:
    """1つのボイス設定を表すデータクラス"""
    name: str
    display_name: str
    description: str
    kokoro_voice: str  # Kokoro-82M の voice ID
    lang_code: str = "j"  # j = Japanese
    speed: float = 1.0
    pitch_shift: float = 0.0  # 半音単位（将来の拡張用）
    emotion_voices: Dict[str, str] = field(default_factory=dict)
    # 感情に応じてボイスを変える場合のマッピング


# AURA のデフォルトボイスプロファイル
AURA_DEFAULT = VoiceProfile(
    name="aura_default",
    display_name="AURA（デフォルト）",
    description="AURAの標準ボイス。明るく親しみやすい女性の声。",
    kokoro_voice="jf_alpha",
    speed=1.05,  # 少し速めでテンポ良く
    emotion_voices={
        "happy": "jf_nezumi",      # 活発な声で嬉しさを表現
        "sad": "jf_tebukuro",      # 落ち着いた声で悲しさを表現
        "neutral": "jf_alpha",
        "thinking": "jf_alpha",
        "surprised": "jf_nezumi",
    }
)

AURA_GENTLE = VoiceProfile(
    name="aura_gentle",
    display_name="AURA（穏やか）",
    description="AURAの穏やかボイス。柔らかく優しい声。",
    kokoro_voice="jf_gongitsune",
    speed=0.95,
)

AURA_ENERGETIC = VoiceProfile(
    name="aura_energetic",
    display_name="AURA（元気）",
    description="AURAの元気ボイス。明るく弾むような声。",
    kokoro_voice="jf_nezumi",
    speed=1.1,
)

# 利用可能なプロファイル一覧
VOICE_PROFILES: Dict[str, VoiceProfile] = {
    "aura_default": AURA_DEFAULT,
    "aura_gentle": AURA_GENTLE,
    "aura_energetic": AURA_ENERGETIC,
}


# ============================================================
# 拡張 TTS サービス
# ============================================================

class AuraVoiceService:
    """
    AURA専用の音声合成サービス。
    Kokoro-82M をベースに、感情に応じたボイス切り替えと
    音声加工（ピッチ、速度）を行う。
    """

    def __init__(self, profile_name: str = "aura_default"):
        self.pipeline = None
        self.current_profile = VOICE_PROFILES.get(profile_name, AURA_DEFAULT)
        self.sample_rate = 24000

    def _load_pipeline(self):
        """Kokoro パイプラインを遅延ロード"""
        if self.pipeline is None:
            try:
                from kokoro import KPipeline
                logger.info(f"Loading Kokoro pipeline (lang={self.current_profile.lang_code})...")
                self.pipeline = KPipeline(lang_code=self.current_profile.lang_code)
                logger.info("Kokoro pipeline loaded successfully.")
            except ImportError:
                logger.error(
                    "Kokoro is not installed. "
                    "Install with: pip install 'kokoro>=0.9.4' 'misaki[ja]'"
                )
                raise

    def set_profile(self, profile_name: str):
        """ボイスプロファイルを切り替え"""
        if profile_name in VOICE_PROFILES:
            self.current_profile = VOICE_PROFILES[profile_name]
            logger.info(f"Voice profile changed to: {self.current_profile.display_name}")
        else:
            logger.warning(f"Unknown profile: {profile_name}")

    def get_voice_for_emotion(self, emotion: str = "neutral") -> str:
        """感情に応じたボイスIDを取得"""
        if self.current_profile.emotion_voices:
            return self.current_profile.emotion_voices.get(
                emotion, self.current_profile.kokoro_voice
            )
        return self.current_profile.kokoro_voice

    def synthesize(self, text: str, emotion: str = "neutral") -> bytes:
        """
        テキストを音声に変換する。

        Args:
            text: 合成するテキスト
            emotion: 感情（happy, sad, neutral, thinking, surprised）

        Returns:
            WAVフォーマットのバイトデータ
        """
        if not text or not text.strip():
            return b""

        self._load_pipeline()

        voice = self.get_voice_for_emotion(emotion)
        speed = self.current_profile.speed

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
                return b""

            combined_audio = np.concatenate(audio_segments)

            # WAVに変換
            buffer = io.BytesIO()
            sf.write(buffer, combined_audio, self.sample_rate, format='WAV')
            return buffer.getvalue()

        except Exception as e:
            logger.error(f"TTS synthesis error: {e}")
            return b""

    def synthesize_base64(self, text: str, emotion: str = "neutral") -> str:
        """テキストを音声に変換し、base64文字列で返す"""
        audio_bytes = self.synthesize(text, emotion)
        if not audio_bytes:
            return ""
        return base64.b64encode(audio_bytes).decode("utf-8")

    def list_profiles(self) -> List[Dict[str, str]]:
        """利用可能なボイスプロファイル一覧を返す"""
        return [
            {
                "name": p.name,
                "display_name": p.display_name,
                "description": p.description,
            }
            for p in VOICE_PROFILES.values()
        ]
