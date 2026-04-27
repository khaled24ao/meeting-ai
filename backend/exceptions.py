"""
Custom exception hierarchy for MeetingAI application.

Provides specific exception types for different error categories
to enable appropriate HTTP status code mapping.
"""


class MeetingAIError(Exception):
    """Base exception class for all MeetingAI errors."""
    pass


class ValidationError(MeetingAIError):
    """Raised when input validation fails (400 Bad Request)."""
    pass


class TranscriptionError(MeetingAIError):
    """Raised when audio transcription fails (500 Internal Server Error)."""
    pass


class AIServiceError(MeetingAIError):
    """Raised when AI service encounters an error (503 Service Unavailable)."""
    pass


class FileProcessingError(MeetingAIError):
    """Raised when file processing fails (400 Bad Request)."""
    pass