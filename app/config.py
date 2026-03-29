from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    FLIGHTAPI_KEY: str = ""
    GROK_API_KEY: str = ""
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    DATABASE_URL: str = "sqlite:///./track_flights.db"
    CHECK_INTERVAL_HOURS: int = 6

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
