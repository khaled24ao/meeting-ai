import whisper
import logging
from typing import Set


ALLOWED_EXTENSIONS: Set[str] = {'mp3', 'mp4', 'wav', 'm4a'}

logger = logging.getLogger(__name__)


def allowed_file(filename: str) -> bool:
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS


class WhisperService:
    def __init__(self, model_size: str = "tiny") -> None:
        self.model = whisper.load_model(model_size)

    def transcribe(self, audio_path: str) -> str:
        try:
            result = self.model.transcribe(audio_path)
            return result.get("text", "").strip()
        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            raise Exception(f"Transcription failed: {str(e)}")