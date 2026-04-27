"""
API routes for meeting summarization functionality.

Provides endpoint for analyzing meetings via audio upload or text transcript.
Implements input validation, error handling, and standardized responses.
"""
from flask import Blueprint, request, jsonify, g, Response
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from typing import Optional, Tuple, Any, Dict, List, Union
import os
import logging
import re
from datetime import datetime
from pydantic import BaseModel, field_validator, ValidationError as PydanticValidationError

from backend.config import config
from backend.constants import MAX_UPLOAD_BYTES, MAX_UPLOAD_SIZE_MB, MAX_TRANSCRIPT_LENGTH, PROMPT_TEMPLATE
from backend.services.ai_service import AIService, AIServiceError
from backend.services.whisper_service import WhisperService, allowed_file
from backend.exceptions import ValidationError, TranscriptionError
from backend.utils.auth import authenticate_api_key, rate_limit

logger = logging.getLogger(__name__)

# Create blueprint for summarize endpoints
summarize_bp = Blueprint('summarize', __name__)

# Service singleton instances
_ai_service: Optional[AIService] = None
_whisper_service: Optional[WhisperService] = None

# System prompt for AI analysis (imported from constants)
PROMPT: str = PROMPT_TEMPLATE


# --- Pydantic models for input validation ---

class TextInputModel(BaseModel):
    """Pydantic model for validating text input."""
    text: str

    @field_validator('text')
    @classmethod
    def text_must_be_nonempty(cls, v: str) -> str:
        """Validate that text is not empty or whitespace only."""
        if not v or not v.strip():
            raise ValueError('Text input cannot be empty')
        return v


# --- Service getters ---

def get_ai_service() -> Optional[AIService]:
    """
    Get or initialize the AI service singleton.
    
    Returns:
        AIService instance or None if initialization failed.
    """
    global _ai_service
    if _ai_service is None:
        try:
            logger.info("Initializing AI service with model: %s", config.ai_model)
            _ai_service = AIService(
                model=config.ai_model,
                temperature=config.ai_temperature,
                max_tokens=config.ai_max_tokens
            )
        except AIServiceError as e:
            logger.error("Failed to initialize AI service: %s", e)
            return None
        except Exception as e:
            logger.error("Unexpected error initializing AI service: %s", e, exc_info=True)
            return None
    return _ai_service


def get_whisper_service() -> Optional[WhisperService]:
    """
    Get or initialize the Whisper service singleton.
    
    Returns:
        WhisperService instance or None if initialization failed.
    """
    global _whisper_service
    if _whisper_service is None:
        try:
            logger.info("Initializing Whisper service with model: %s", config.whisper_model)
            _whisper_service = WhisperService(model_size=config.whisper_model)
        except Exception as e:
            logger.error("Failed to initialize Whisper service: %s", e)
            return None
    return _whisper_service


# --- File validation ---

def validate_file(file: Optional[FileStorage]) -> None:
    """
    Validate uploaded file exists and has valid filename.
    
    Args:
        file: FileStorage object to validate.
        
    Raises:
        ValidationError: If file is None, has no filename, or has invalid extension.
    """
    if not file:
        logger.warning("No file provided in request")
        raise ValidationError("No file provided")
    
    if not file.filename:
        logger.warning("File uploaded with empty filename")
        raise ValidationError("Empty filename")
    
    if not allowed_file(file.filename):
        allowed_list = ', '.join(config.allowed_extensions)
        logger.warning("Invalid file type: %s. Allowed: %s", file.filename, allowed_list)
        raise ValidationError(f"Invalid file type. Allowed: {allowed_list}")


def validate_request_size() -> None:
    """
    Validate that request content length does not exceed configured limit.
    
    Raises:
        ValidationError: If request exceeds maximum allowed size.
    """
    content_length = request.content_length
    if content_length and content_length > MAX_UPLOAD_BYTES:
        max_mb = MAX_UPLOAD_SIZE_MB
        logger.warning("Upload rejected: %d bytes exceeds limit of %d MB", 
                      content_length, max_mb)
        raise ValidationError(f"File too large. Max {max_mb}MB allowed")


# --- File operations ---

def save_uploaded_file(upload_folder: str, file: FileStorage) -> str:
    """
    Save uploaded file to the uploads directory using a secure filename.
    
    Args:
        upload_folder: Directory to save file in.
        file: FileStorage object to save.
        
    Returns:
        str: Full path to saved file.
    """
    try:
        os.makedirs(upload_folder, exist_ok=True)
        # Sanitize filename to prevent directory traversal
        if not file.filename:
             raise ValidationError("Empty filename")
        safe_filename = secure_filename(file.filename)
        if not safe_filename:
            raise ValidationError("Invalid filename")
        filepath = os.path.join(upload_folder, safe_filename)
        logger.info("Saving uploaded file to: %s", filepath)
        file.save(filepath)
        return filepath
    except Exception as e:
        logger.error("Failed to save uploaded file: %s", str(e), exc_info=True)
        raise ValidationError(f"Failed to save uploaded file: {str(e)}")


# --- Transcription ---

def transcribe_audio_file(whisper_service: WhisperService, filepath: str) -> str:
    """
    Transcribe an audio file and handle cleanup.
    
    Args:
        whisper_service: Initialized WhisperService instance.
        filepath: Path to the audio file.
        
    Returns:
        str: Transcribed text content.
        
    Raises:
        TranscriptionError: If transcription fails.
    """
    logger.info("Starting transcription for: %s", filepath)
    
    try:
        transcript = whisper_service.transcribe(filepath)
        
        if not transcript:
            logger.warning("Transcription returned empty result")
            raise TranscriptionError("Could not transcribe audio file - no text extracted")
        
        logger.info("Transcription successful: %d characters", len(transcript))
        return transcript
        
    except TranscriptionError:
        raise
    except Exception as e:
        logger.error("Transcription error: %s", e, exc_info=True)
        raise TranscriptionError(f"Transcription failed: {str(e)}") from e
    finally:
        # Always clean up uploaded file
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                logger.debug("Cleaned up uploaded file: %s", filepath)
            except OSError as e:
                logger.warning("Failed to delete file %s: %s", filepath, e)


# --- Text processing ---

def sanitize_text(text: str) -> str:
    """
    Sanitize user-provided text by removing control characters.
    
    Args:
        text: Raw input text.
        
    Returns:
        str: Sanitized text safe for processing.
    """
    # Remove null bytes and control characters (except newline, tab, carriage return)
    sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    return sanitized.strip()


def truncate_text_content(text: str, max_length: int) -> str:
    """
    Truncate text to maximum allowed length.
    
    Args:
        text: Input text to truncate.
        max_length: Maximum allowed character count.
        
    Returns:
        str: Truncated text.
    """
    if len(text) > max_length:
        logger.info("Truncating input from %d to %d characters", len(text), max_length)
        return text[:max_length]
    return text


# --- AI analysis ---

def analyze_with_ai(ai_service: AIService, transcript: str, prompt: str) -> str:
    """
    Send transcript to AI service for analysis.
    
    Args:
        ai_service: Initialized AIService instance.
        transcript: Text content to analyze.
        prompt: System prompt for AI analysis.
        
    Returns:
        str: JSON string with analysis results.
        
    Raises:
        AIServiceError: If AI analysis fails.
    """
    logger.info("Sending transcript to AI service (%d characters)", len(transcript))
    
    try:
        result = ai_service.generate_summary(transcript, prompt)
        logger.info("AI analysis completed successfully")
        return result
    except AIServiceError:
        raise
    except Exception as e:
        logger.error("Unexpected error in analyze_with_ai: %s", str(e), exc_info=True)
        raise AIServiceError(f"AI analysis failed: {str(e)}")


# --- Standardized response helpers ---

def json_success(data: Any, status: int = 200) -> Tuple[Response, int]:
    """
    Create a standardized success response.
    
    Args:
        data: Response payload data.
        status: HTTP status code (default 200).
        
    Returns:
        tuple: (jsonify response, status code)
    """
    return jsonify({
        'success': True,
        'data': data
    }), status


def json_error(message: str, error_code: str, status: int) -> Tuple[Response, int]:
    """
    Create a standardized error response.
    
    Args:
        message: Human-readable error message.
        error_code: Machine-readable error identifier.
        status: HTTP status code.
        
    Returns:
        tuple: (jsonify response, status code)
    """
    return jsonify({
        'success': False,
        'error': error_code,
        'message': message
    }), status


# --- Main endpoint ---

@summarize_bp.route('/summarize', methods=['POST'])
@authenticate_api_key
def summarize() -> Union[Tuple[Response, int], Any]:
    """
    Analyze meeting content from audio file or text transcript.
    
    Accepts multipart form data with either:
    - 'file': Audio file (mp3, wav, m4a, mp4, max 25MB)
    - 'text': Plain text transcript
    
    Returns:
        tuple: (JSON response, HTTP status code)
        
    Success Response (200 OK):
        {
            "success": true,
            "data": {
                "result": "{\"summary\": \"...\", ...}",
                "transcript_length": 1234
            }
        }
        
    Error Responses:
        400: Invalid input (ValidationError)
        503: Service unavailable (AIServiceError, Whisper unavailable)
        500: Internal error (TranscriptionError, unexpected exceptions)
    """
    logger.info("Received summarization request")
    
    try:
        # Check rate limit
        allowed, info = rate_limit()
        if not allowed:
            return json_error(
                message='Rate limit exceeded',
                error_code='RATE_LIMIT_EXCEEDED',
                status=429
            )

        # Check AI service availability
        ai_service = get_ai_service()
        if ai_service is None:
            logger.error("AI service unavailable - returning 503")
            return json_error(
                message='AI analysis service is currently unavailable. Check GROQ_API_KEY configuration.',
                error_code='AI_SERVICE_UNAVAILABLE',
                status=503
            )
        
        # Extract input from request
        text_input = request.form.get('text', '').strip()
        uploaded_file = request.files.get('file')
        
        logger.debug("Request data - text length: %d, file: %s", 
                    len(text_input), 
                    uploaded_file.filename if uploaded_file else 'None')
        
        transcript = ""

        # Process text input if provided
        if text_input:
            logger.info("Processing text input (%d characters)", len(text_input))
            
            # Validate with Pydantic model
            try:
                validated = TextInputModel(text=text_input)
                text_input = validated.text
            except PydanticValidationError as e:
                logger.warning("Text validation failed: %s", e)
                return json_error(
                    message=str(e),
                    error_code='VALIDATION_ERROR',
                    status=400
                )
            
            # Sanitize and truncate
            clean_text = sanitize_text(text_input)
            transcript = truncate_text_content(clean_text, MAX_TRANSCRIPT_LENGTH)
        
        # Process file upload if provided
        elif uploaded_file:
            logger.info("Processing file upload: %s", uploaded_file.filename)
            
            # Validate file
            try:
                validate_file(uploaded_file)
                validate_request_size()
            except ValidationError as e:
                logger.warning("File validation failed: %s", e)
                return json_error(
                    message=str(e),
                    error_code='VALIDATION_ERROR',
                    status=400
                )
            
            # Save file with safe filename
            upload_folder = config.upload_folder
            filepath = save_uploaded_file(upload_folder, uploaded_file)
            
            # Get Whisper service
            whisper_service = get_whisper_service()
            if whisper_service is None:
                logger.error("Whisper service unavailable - returning 503")
                # Clean up uploaded file since we won't process it
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                        logger.debug("Cleaned up file after service failure: %s", filepath)
                    except OSError as e:
                        logger.warning("Failed to delete file %s: %s", filepath, e)
                return json_error(
                    message='Transcription service is currently unavailable',
                    error_code='SERVICE_UNAVAILABLE',
                    status=503
                )
            
            # Transcribe and cleanup
            try:
                transcript = transcribe_audio_file(whisper_service, filepath)
            except TranscriptionError as e:
                logger.error("Transcription failed: %s", e)
                return json_error(
                    message=str(e),
                    error_code='TRANSCRIPTION_ERROR',
                    status=500
                )
            
            # Truncate transcript if needed
            transcript = truncate_text_content(transcript, MAX_TRANSCRIPT_LENGTH)
        
        else:
            logger.warning("Request missing both file and text parameters")
            return json_error(
                message='No audio file or text provided',
                error_code='VALIDATION_ERROR',
                status=400
            )
        
        if not transcript:
             return json_error(
                message='No transcript extracted from input',
                error_code='EMPTY_TRANSCRIPT',
                status=400
            )

        # Generate analysis using AI
        try:
            analysis_result = analyze_with_ai(ai_service, transcript, PROMPT.format(text=transcript))
            response_data = {
                'result': analysis_result,
                'transcript_length': len(transcript)
            }
            logger.info("Request completed successfully")
            return json_success(response_data, status=200)
            
        except AIServiceError as e:
            logger.error("AI analysis failed: %s", e)
            return json_error(
                message=str(e),
                error_code='AI_SERVICE_ERROR',
                status=500
            )
        except Exception as e:
            logger.error("Unexpected error during AI analysis: %s", e, exc_info=True)
            return json_error(
                message='AI analysis failed due to an unexpected error',
                error_code='INTERNAL_SERVER_ERROR',
                status=500
            )
    except Exception as e:
        logger.error("Unexpected error in summarize endpoint: %s", e, exc_info=True)
        return json_error(
            message='An unexpected error occurred',
            error_code='INTERNAL_SERVER_ERROR',
            status=500
        )


@summarize_bp.route('/health', methods=['GET'])
def health_check() -> Tuple[Response, int]:
    """
    Health check endpoint for Docker container monitoring.
    
    Returns:
        tuple: (JSON response, HTTP 200)
    """
    try:
        return jsonify({
            'status': 'healthy',
            'service': 'MeetingAI',
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }), 200
    except Exception as e:
        logger.error("Health check failed: %s", str(e))
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500