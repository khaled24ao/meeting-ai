"""
Application constants for MeetingAI.

Centralized configuration of all magic numbers, strings, and static values.
"""

# File upload settings
ALLOWED_EXTENSIONS: set[str] = {'mp3', 'mp4', 'wav', 'm4a'}
MAX_UPLOAD_SIZE_MB: int = 25
MAX_UPLOAD_BYTES: int = MAX_UPLOAD_SIZE_MB * 1024 * 1024

# Transcription settings
MAX_TRANSCRIPT_LENGTH: int = 4000
DEFAULT_WHISPER_MODEL: str = 'tiny'

# AI settings
DEFAULT_AI_MODEL: str = 'llama3-8b-8192'
DEFAULT_AI_TEMPERATURE: float = 0.5
DEFAULT_AI_MAX_TOKENS: int = 1024

# Logging
DEFAULT_LOG_LEVEL: str = 'INFO'
DEFAULT_LOG_FORMAT: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# System prompt for AI analysis
PROMPT_TEMPLATE: str = """You are a PRECISE meeting analyst. Your output MUST be accurate.

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

# API response messages
ERROR_NO_INPUT: str = 'No audio file or text provided'
ERROR_INVALID_FILE_TYPE: str = 'Invalid file type'
ERROR_FILE_TOO_LARGE: str = 'File too large'
ERROR_TRANSCRIPTION_FAILED: str = 'Transcription failed'
ERROR_AI_SERVICE_UNAVAILABLE: str = 'AI service not available'
ERROR_TRANSCRIPTION_SERVICE_UNAVAILABLE: str = 'Transcription service not available'
ERROR_EMPTY_TEXT: str = 'Empty text provided'

# HTTP status codes (for reference)
HTTP_OK: int = 200
HTTP_BAD_REQUEST: int = 400
HTTP_UNAUTHORIZED: int = 401
HTTP_FORBIDDEN: int = 403
HTTP_NOT_FOUND: int = 404
HTTP_INTERNAL_SERVER_ERROR: int = 500
HTTP_SERVICE_UNAVAILABLE: int = 503
