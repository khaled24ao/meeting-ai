"""
Audio transcription service using OpenAI Whisper.

Provides speech-to-text conversion for supported audio formats.
"""
import whisper
import logging
from typing import Set, Any

from backend.constants import ALLOWED_EXTENSIONS
from backend.exceptions import TranscriptionError

logger = logging.getLogger(__name__)


def allowed_file(filename: str) -> bool:
    """
    Check if file extension is allowed for upload.
    
    Args:
        filename: Name of the file to validate.
        
    Returns:
        bool: True if extension is allowed, False otherwise.
    """
    try:
        if not filename or '.' not in filename:
            logger.debug("Filename missing or has no extension: %s", filename)
            return False
        
        ext = filename.rsplit('.', 1)[1].lower()
        is_allowed = ext in ALLOWED_EXTENSIONS
        
        if not is_allowed:
            logger.debug("File extension '%s' not in allowed list: %s", ext, ALLOWED_EXTENSIONS)
        
        return is_allowed
    except Exception as e:
        logger.error("Error checking file extension: %s", str(e))
        return False


class WhisperService:
    """
    Service for transcribing audio files using Whisper model.
    
    Loads a Whisper model on initialization and provides transcription
    functionality for supported audio formats.
    
    Attributes:
        model: Loaded Whisper model instance.
        model_size: Size of the Whisper model (tiny/base/small/medium/large).
    """
    
    def __init__(self, model_size: str = "tiny") -> None:
        """
        Initialize Whisper service by loading the specified model.
        
        Args:
            model_size: Size of Whisper model to load.
                Options: tiny, base, small, medium, large.
                
        Note:
            Model is loaded synchronously on initialization which may
            take several seconds depending on model size.
        """
        try:
            logger.info("Loading Whisper model: %s", model_size)
            self.model: Any = whisper.load_model(model_size)
            self.model_size: str = model_size
            logger.info("Whisper model %s loaded successfully", model_size)
        except Exception as e:
            logger.error("Failed to load Whisper model %s: %s", model_size, str(e), exc_info=True)
            raise TranscriptionError(f"Failed to initialize transcription service: {str(e)}")

    def transcribe(self, audio_path: str) -> str:
        """
        Transcribe an audio file to text.
        
        Args:
            audio_path: Path to the audio file to transcribe.
            
        Returns:
            str: Transcribed text content.
            
        Raises:
            TranscriptionError: If transcription fails for any reason including
                file not found, unsupported format, or model errors.
        """
        logger.info("Starting transcription for file: %s", audio_path)
        
        try:
            result: dict[str, Any] = self.model.transcribe(audio_path)
            transcript: str = result.get("text", "").strip()
            
            if transcript:
                logger.info("Transcription complete: %d characters", len(transcript))
            else:
                logger.warning("Transcription produced empty result for %s", audio_path)
            
            return transcript
            
        except FileNotFoundError:
            logger.error("Audio file not found: %s", audio_path)
            raise TranscriptionError(f"Audio file not found: {audio_path}")
        except Exception as e:
            logger.error("Whisper transcription failed for %s: %s", audio_path, e, exc_info=True)
            raise TranscriptionError(f"Transcription failed: {str(e)}")