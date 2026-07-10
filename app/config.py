from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(
        default="postgresql+psycopg://callsight:callsight@localhost:5432/callsight",
        alias="DATABASE_URL",
    )
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    huggingface_access_token: str | None = Field(
        default=None, alias="HUGGINGFACE_ACCESS_TOKEN"
    )
    whisper_model_size: str = Field(default="base", alias="WHISPER_MODEL_SIZE")
    whisper_device: str = Field(default="cpu", alias="WHISPER_DEVICE")
    whisper_compute_type: str = Field(default="int8", alias="WHISPER_COMPUTE_TYPE")
    diarization_model: str = Field(
        default="pyannote/speaker-diarization-community-1",
        alias="DIARIZATION_MODEL",
    )
    use_mock_transcript: bool = Field(default=True, alias="USE_MOCK_TRANSCRIPT")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
