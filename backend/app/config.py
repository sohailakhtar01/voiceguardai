from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App configuration, loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", protected_namespaces=()
    )

    # "mock" (default, no ML) | "wav2vec2" (real pretrained model)
    detector_engine: str = "mock"
    wav2vec2_model: str = "motheecreator/Deepfake-audio-detection"

    # Supabase (used from Phase 4)
    supabase_url: str = ""
    supabase_key: str = ""


settings = Settings()
