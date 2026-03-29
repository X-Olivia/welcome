from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str = ""
    openai_model: str = "gpt-5-mini"
    openai_base_url: str = ""
    assemblyai_api_key: str = ""
    assemblyai_base_url: str = "https://api.assemblyai.com/v2"
    assemblyai_poll_interval_ms: int = 1000
    assemblyai_poll_attempts: int = 60
    cartesia_api_key: str = ""
    cartesia_base_url: str = "https://api.cartesia.ai"
    cartesia_version: str = "2025-04-16"
    cartesia_model_id: str = "sonic-3"
    cartesia_voice_id: str = "f786b574-daa5-4673-aa0c-cbe3e8534c02"
    cartesia_language: str = "en"
    cartesia_speed: float = 1.0
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    public_base_url: str = "http://localhost:5173"
    arm_mock: bool = True
    # e.g. http://127.0.0.1:8765 — after a route is built, POST 8-way action_key to arm_daemon
    arm_daemon_url: str = ""
    # Extra rotation (deg) for polyline→compass if map north ≠ screen-up convention
    arm_map_north_offset_deg: float = 0.0
    arm_daemon_timeout_sec: float = 3.0


settings = Settings()
