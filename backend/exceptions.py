class MeetingAIError(Exception):
    pass


class ValidationError(MeetingAIError):
    pass


class TranscriptionError(MeetingAIError):
    pass


class AIServiceError(MeetingAIError):
    pass


class FileProcessingError(MeetingAIError):
    pass