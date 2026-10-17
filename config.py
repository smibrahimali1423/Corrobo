import logging
import secrets
from functools import lru_cache

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env into os.environ (not just into Settings) so the google-genai SDK,
# which reads GEMINI_API_KEY from the environment itself, sees it too.
load_dotenv()

logger = logging.getLogger("corrobo")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    database_url: str = "postgresql://corrobo:changeme@localhost:5432/corrobo"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash"
    max_claims_per_check: int = 25

    jwt_secret: str = ""
    jwt_expire_minutes: int = 60 * 24

    chroma_path: str = "./chroma_data"
    frontend_dist: str = "./frontend/dist"
    cors_origins: str = "http://localhost:5173"

    @property
    def llm_configured(self) -> bool:
        return bool(self.gemini_api_key.strip())

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if not settings.jwt_secret:
        # Dev convenience: the app still boots, but every restart invalidates
        # existing tokens. Production must set JWT_SECRET (see docs/DEPLOYMENT.md).
        logger.warning("JWT_SECRET is not set; using an ephemeral random secret.")
        settings.jwt_secret = secrets.token_urlsafe(32)
    return settings
