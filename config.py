"""
Application configuration, loaded from environment variables.
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class AppConfig:
    """Application configuration with defaults."""
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    gradio_server_name: str = "127.0.0.1"
    gradio_server_port: int = 7860
    max_file_size_mb: int = 10
    demo_mode: bool = False
    db_path: str = "interview_history.db"
    enable_history: bool = True

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Load configuration from .env file and environment variables."""
        load_dotenv()
        config = cls(
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            gradio_server_name=os.getenv("GRADIO_SERVER_NAME", "127.0.0.1"),
            gradio_server_port=int(os.getenv("GRADIO_SERVER_PORT", "7860")),
            max_file_size_mb=int(os.getenv("MAX_FILE_SIZE_MB", "10")),
            db_path=os.getenv("DB_PATH", "interview_history.db"),
            enable_history=os.getenv("ENABLE_HISTORY", "true").lower() == "true",
        )
        if not config.openai_api_key:
            config.demo_mode = True
        return config

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024


def get_config() -> AppConfig:
    """Get the application configuration singleton."""
    return AppConfig.from_env()
