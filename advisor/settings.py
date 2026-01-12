from pydantic_settings import BaseSettings, SettingsConfigDict


class SQLSettings(BaseSettings):
    pool_size: int = 3
    max_overflow: int = 10
    pool_recycle: int = 270


class ProjectSettings(BaseSettings):

    sql_connection_url: str | None = None

    class Config:
        env_file = ".env"
