from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "StudyLink"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/studylink"
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    extension_token_expire_days: int = 90

    apple_team_id: str = ""
    apple_client_id: str = ""
    apple_key_id: str = ""
    apple_private_key: str = ""

    google_client_id: str = ""
    google_client_secret: str = ""
    google_extension_redirect_uri: str = "https://api.studylink.app/auth/google/extension-callback"

    api_base_url: str = "https://api.studylink.app"

    class Config:
        env_file = ".env"


settings = Settings()
