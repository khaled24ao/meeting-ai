from flask import Blueprint, request, jsonify
from werkzeug.datastructures import FileStorage
from typing import Optional
import os
import logging

from backend.config import config
from backend.services.ai_service import AIService, AIServiceError
from backend.services.whisper_service import WhisperService, allowed_file
from backend.exceptions import ValidationError, TranscriptionError

logger = logging.getLogger(__name__)

summarize_bp = Blueprint('summarize', __name__)

_ai_service = None
_whisper_service = None


def get_ai_service():
    global _ai_service
    if _ai_service is None:
        try:
            _ai_service = AIService(
                model=config.ai_model,
                temperature=config.ai_temperature,
                max_tokens=config.ai_max_tokens
            )
        except AIServiceError as e:
            logger.error(f"Failed to initialize AI service: {e}")
            return None
    return _ai_service


def get_whisper_service():
    global _whisper_service
    if _whisper_service is None:
        try:
            _whisper_service = WhisperService(model_size=config.whisper_model)
        except Exception as e:
            logger.error(f"Failed to initialize Whisper service: {e}")
            return None
    return _whisper_service

PROMPT = """You are a PRECISE meeting analyst. Your output MUST be accurate.

CRITICAL RULES - FOLLOW EXACTLY:
1. PROPOSAL vs DECISION: 
   - "should", "could", "maybe", "we might", "I suggest" = PROPOSAL (ignore or mark as proposed)
   - "agreed", "decided", "OK let's", "will do", "going to" = DECISION
   - If someone REJECTS a proposal ("that's too much", "let's do X instead") → the REVISED version is the decision
   
2. DEADLINES: Extract explicit deadlines only. If someone says "today", "tomorrow", "next week", use that. Otherwise use "TBD" - NEVER guess.

3. ALWAYS extract implicit tasks:
   - "let's meet again" / "review progress" / "check back in X days" → follow-up task with deadline
   - "we need to..." → implicit task

4. ALWAYS extract risks (worries, concerns, problems, slow, overwhelmed, issues, challenges)

5. Duration: Only use "explicit" if duration mentioned. Otherwise use "Unknown" - NEVER guess numbers.

Output format (VALID JSON ONLY):
{{
  "summary": "What was actually DECIDED",
  "action_items": [{{"task": "specific actionable task", "owner": "person name", "deadline": "explicit date or TBD"}}],
  "decisions": [{{"decision": "what was agreed"}}],
  "risks": ["explicit concerns mentioned"],
  "key_topics": ["topics discussed"],
  "duration_estimate": "explicit time or Unknown"
}}

TRANSCRIPT:
{text}"""


def validate_file(file: Optional[FileStorage]) -> None:
    if not file:
        raise ValidationError("No file provided")
    if not file.filename:
        raise ValidationError("Empty filename")
    if not allowed_file(file.filename):
        raise ValidationError(f"Invalid file type. Allowed: {', '.join(config.allowed_extensions)}")


def validate_size(file: FileStorage) -> None:
    content_length = request.content_length
    if content_length and content_length > config.max_upload_size:
        raise ValidationError(f"File too large. Max {config.max_upload_size // (1024*1024)}MB allowed")


@summarize_bp.route('/summarize', methods=['POST'])
def summarize() -> tuple:
    ai_svc = get_ai_service()
    if ai_svc is None:
        return jsonify({'error': 'AI service not available. Check GROQ_API_KEY'}), 503
    
    text_input = request.form.get('text') or ''
    text_input = text_input.strip()
    file = request.files.get('file')

    logger.info(f"Request received - text: {len(text_input)} chars, file: {file.filename if file else None}")

    if text_input:
        transcript = text_input[:config.max_transcript_length]
    elif file:
        whisper_svc = get_whisper_service()
        if whisper_svc is None:
            return jsonify({'error': 'Transcription service not available'}), 503
        
        try:
            validate_file(file)
            validate_size(file)
        except ValidationError as e:
            return jsonify({'error': str(e)}), 400

        upload_folder = config.upload_folder
        os.makedirs(upload_folder, exist_ok=True)
        filepath = os.path.join(upload_folder, file.filename)
        file.save(filepath)

        try:
            transcript = whisper_svc.transcribe(filepath)
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({'error': f'Transcription failed: {str(e)}'}), 500
        
        if not transcript:
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({'error': 'Could not transcribe audio file'}), 400
        
        if os.path.exists(filepath):
            os.remove(filepath)
        
        transcript = transcript[:config.max_transcript_length]
    else:
        return jsonify({'error': 'No audio file or text provided'}), 400

    try:
        result = ai_svc.generate_summary(transcript, PROMPT.format(text=transcript))
        return jsonify({'result': result, 'transcript_length': len(transcript)}), 200
    except AIServiceError as e:
        logger.error(f"AI Service error: {e}")
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500