from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BOT_TOKEN: str

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
