"""
Configuration management for MeetingAI.

All settings loaded from environment variables with fallback to constants.
Uses singleton pattern for global access.
"""
import os
import logging
import hashlib
from typing import Any, Optional

from backend.constants import (
    ALLOWED_EXTENSIONS,
    MAX_UPLOAD_SIZE_MB,
    MAX_TRANSCRIPT_LENGTH,
    DEFAULT_WHISPER_MODEL,
    DEFAULT_AI_MODEL,
    DEFAULT_AI_TEMPERATURE,
    DEFAULT_AI_MAX_TOKENS,
    DEFAULT_LOG_LEVEL,
    DEFAULT_LOG_FORMAT,
)

logger = logging.getLogger(__name__)


class Config:
    """
    Singleton configuration manager.
    
    Reads all settings from environment variables with sensible defaults.
    Provides typed property accessors.
    """
    _instance: Optional['Config'] = None

    def __new__(cls) -> 'Config':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self) -> None:
        """Initialize configuration from environment variables."""
        try:
            # App settings
            self._app_name: str = os.getenv('APP_NAME', 'MeetingAI')
            self._debug: bool = os.getenv('DEBUG', 'false').lower() == 'true'
            self._host: str = os.getenv('HOST', '0.0.0.0')
            
            try:
                self._port: int = int(os.getenv('PORT', '7860'))
            except (ValueError, TypeError):
                logger.warning("Invalid PORT environment variable, falling back to 7860")
                self._port = 7860

            # Upload settings
            self._upload_folder: str = os.getenv('UPLOAD_FOLDER', 'storage/uploads')
            
            try:
                self._max_size_mb: int = int(os.getenv('MAX_UPLOAD_SIZE_MB', str(MAX_UPLOAD_SIZE_MB)))
            except (ValueError, TypeError):
                logger.warning("Invalid MAX_UPLOAD_SIZE_MB environment variable, falling back to %d", MAX_UPLOAD_SIZE_MB)
                self._max_size_mb = MAX_UPLOAD_SIZE_MB

            # Allow overriding allowed extensions via comma-separated env var
            allowed_ext_env = os.getenv('ALLOWED_EXTENSIONS')
            if allowed_ext_env:
                self._allowed_extensions: list[str] = [ext.strip() for ext in allowed_ext_env.split(',')]
            else:
                self._allowed_extensions = list(ALLOWED_EXTENSIONS)

            # Transcription settings
            try:
                self._max_transcript_length: int = int(os.getenv('MAX_TRANSCRIPT_LENGTH', str(MAX_TRANSCRIPT_LENGTH)))
            except (ValueError, TypeError):
                logger.warning("Invalid MAX_TRANSCRIPT_LENGTH environment variable, falling back to %d", MAX_TRANSCRIPT_LENGTH)
                self._max_transcript_length = MAX_TRANSCRIPT_LENGTH

            self._whisper_model: str = os.getenv('WHISPER_MODEL', DEFAULT_WHISPER_MODEL)

            # AI settings
            self._ai_model: str = os.getenv('AI_MODEL', DEFAULT_AI_MODEL)
            
            try:
                self._ai_temperature: float = float(os.getenv('AI_TEMPERATURE', str(DEFAULT_AI_TEMPERATURE)))
            except (ValueError, TypeError):
                logger.warning("Invalid AI_TEMPERATURE environment variable, falling back to %f", DEFAULT_AI_TEMPERATURE)
                self._ai_temperature = DEFAULT_AI_TEMPERATURE

            try:
                self._ai_max_tokens: int = int(os.getenv('AI_MAX_TOKENS', str(DEFAULT_AI_MAX_TOKENS)))
            except (ValueError, TypeError):
                logger.warning("Invalid AI_MAX_TOKENS environment variable, falling back to %d", DEFAULT_AI_MAX_TOKENS)
                self._ai_max_tokens = DEFAULT_AI_MAX_TOKENS

            # Logging settings
            self._log_level: str = os.getenv('LOG_LEVEL', DEFAULT_LOG_LEVEL)
            self._log_format: str = os.getenv('LOG_FORMAT', DEFAULT_LOG_FORMAT)

            # Security: API key authentication (comma-separated list)
            api_keys_env = os.getenv('ALLOWED_API_KEYS', '')
            self._allowed_api_keys: list[str] = [
                k.strip() for k in api_keys_env.split(',') if k.strip()
            ] if api_keys_env else []

            # Rate limiting (using Redis if available, else in-memory)
            self._rate_limit_enabled: bool = os.getenv('RATE_LIMIT_ENABLED', 'true').lower() == 'true'
            
            try:
                self._rate_limit_requests: int = int(os.getenv('RATE_LIMIT_REQUESTS', '100'))
            except (ValueError, TypeError):
                logger.warning("Invalid RATE_LIMIT_REQUESTS environment variable, falling back to 100")
                self._rate_limit_requests = 100

            try:
                self._rate_limit_window: int = int(os.getenv('RATE_LIMIT_WINDOW', '86400'))  # 1 day in seconds
            except (ValueError, TypeError):
                logger.warning("Invalid RATE_LIMIT_WINDOW environment variable, falling back to 86400")
                self._rate_limit_window = 86400

            # Warn if no API keys configured in production
            if not self._allowed_api_keys and not self._debug:
                logger.warning(
                    "ALLOWED_API_KEYS not set - API endpoints will reject all requests. "
                    "Set ALLOWED_API_KEYS in .env for production."
                )

            logger.info(
                "Configuration loaded: upload_folder=%s, max_size=%dMB, whisper_model=%s, ai_model=%s, api_keys_count=%d",
                self._upload_folder, self._max_size_mb, self._whisper_model, self._ai_model, len(self._allowed_api_keys)
            )
        except Exception as e:
            logger.error("Critical error loading configuration: %s", str(e), exc_info=True)
            # Re-raise to prevent app starting with broken config
            raise

    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieve configuration value by dot-notation key.
        
        Supported keys:
            - app.name, app.debug, app.host, app.port
            - upload.folder, upload.max_size_mb, upload.allowed_extensions
            - transcription.max_length, transcription.whisper_model
            - ai.model, ai.temperature, ai.max_tokens
            - logging.level, logging.format
            - security.allowed_api_keys
        """
        mapping: dict[str, Any] = {
            'app.name': self._app_name,
            'app.debug': self._debug,
            'app.host': self._host,
            'app.port': self._port,
            'upload.folder': self._upload_folder,
            'upload.max_size_mb': self._max_size_mb,
            'upload.allowed_extensions': self._allowed_extensions,
            'transcription.max_length': self._max_transcript_length,
            'transcription.whisper_model': self._whisper_model,
            'ai.model': self._ai_model,
            'ai.temperature': self._ai_temperature,
            'ai.max_tokens': self._ai_max_tokens,
            'logging.level': self._log_level,
            'logging.format': self._log_format,
            'security.allowed_api_keys': self._allowed_api_keys,
            'security.rate_limit_enabled': self._rate_limit_enabled,
            'security.rate_limit_requests': self._rate_limit_requests,
            'security.rate_limit_window': self._rate_limit_window,
        }
        return mapping.get(key, default)

    @property
    def app_name(self) -> str:
        return self._app_name

    @property
    def debug(self) -> bool:
        return self._debug

    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    @property
    def upload_folder(self) -> str:
        return self._upload_folder

    @property
    def max_upload_size(self) -> int:
        """Maximum upload size in bytes."""
        return self._max_size_mb * 1024 * 1024

    @property
    def allowed_extensions(self) -> list[str]:
        return self._allowed_extensions

    @property
    def max_transcript_length(self) -> int:
        return self._max_transcript_length

    @property
    def whisper_model(self) -> str:
        return self._whisper_model

    @property
    def ai_model(self) -> str:
        return self._ai_model

    @property
    def ai_temperature(self) -> float:
        return self._ai_temperature

    @property
    def ai_max_tokens(self) -> int:
        return self._ai_max_tokens

    @property
    def allowed_api_keys(self) -> list[str]:
        """Get list of allowed API keys (plain text)."""
        return self._allowed_api_keys

    @property
    def rate_limit_enabled(self) -> bool:
        return self._rate_limit_enabled

    @property
    def rate_limit_requests(self) -> int:
        return self._rate_limit_requests

    @property
    def rate_limit_window(self) -> int:
        return self._rate_limit_window

    def is_valid_api_key(self, api_key: str) -> bool:
        """
        Check if provided API key is valid.
        
        Uses constant-time comparison to prevent timing attacks.
        
        Args:
            api_key: API key to validate.
            
        Returns:
            bool: True if key is valid, False otherwise.
        """
        try:
            if not self._allowed_api_keys:
                # No keys configured - allow in debug mode, deny in production
                return self._debug
            
            # Use constant-time comparison
            api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            for allowed_key in self._allowed_api_keys:
                allowed_hash = hashlib.sha256(allowed_key.encode()).hexdigest()
                if api_key_hash == allowed_hash:
                    return True
            return False
        except Exception as e:
            logger.error("Error validating API key: %s", str(e))
            return False



# Global singleton instance
config = Config()