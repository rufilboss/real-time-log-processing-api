from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Defaults target local Docker Compose but can be overridden in K8s/Cloud.
    """

    app_name: str = Field("real-time-log-processing-api", env="APP_NAME")
    log_level: str = Field("INFO", env="LOG_LEVEL")

    mongo_uri: str = Field("mongodb://mongo:27017/log_database", env="MONGO_URI")
    redis_url: str = Field("redis://redis:6379/0", env="REDIS_URL")

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()


