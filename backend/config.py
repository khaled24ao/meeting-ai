import os
import yaml
from typing import Any, Optional
from pathlib import Path


class Config:
    _instance: Optional['Config'] = None
    _config: dict = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self) -> None:
        config_path = os.getenv('CONFIG_PATH', 'config.yaml')
        path = Path(config_path)
        
        if path.exists():
            with open(path, 'r') as f:
                self._config = yaml.safe_load(f) or {}
        else:
            self._config = self._get_defaults()

    def _get_defaults(self) -> dict:
        return {
            'app': {'name': 'MeetingAI', 'debug': False, 'host': '0.0.0.0', 'port': 5000},
            'upload': {'folder': 'storage/uploads', 'max_size_mb': 25, 'allowed_extensions': ['mp3', 'mp4', 'wav', 'm4a']},
            'transcription': {'max_length': 4000, 'whisper_model': 'tiny'},
            'ai': {'provider': 'groq', 'model': 'llama-3.1-8b-instant', 'temperature': 0.5, 'max_tokens': 1024},
            'logging': {'level': 'INFO', 'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'}
        }

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

    @property
    def app_name(self) -> str:
        return self.get('app.name', 'MeetingAI')

    @property
    def debug(self) -> bool:
        return self.get('app.debug', False)

    @property
    def host(self) -> str:
        return self.get('app.host', '0.0.0.0')

    @property
    def port(self) -> int:
        return self.get('app.port', 5000)

    @property
    def upload_folder(self) -> str:
        return self.get('upload.folder', 'storage/uploads')

    @property
    def max_upload_size(self) -> int:
        return self.get('upload.max_size_mb', 25) * 1024 * 1024

    @property
    def allowed_extensions(self) -> list:
        return self.get('upload.allowed_extensions', ['mp3', 'mp4', 'wav', 'm4a'])

    @property
    def whisper_model(self) -> str:
        return self.get('transcription.whisper_model', 'tiny')

    @property
    def max_transcript_length(self) -> int:
        return self.get('transcription.max_length', 4000)

    @property
    def ai_model(self) -> str:
        return self.get('ai.model', 'llama3-8b-8192')

    @property
    def ai_temperature(self) -> float:
        return self.get('ai.temperature', 0.5)

    @property
    def ai_max_tokens(self) -> int:
        return self.get('ai.max_tokens', 1024)


config = Config()