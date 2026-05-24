from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # MQTT
    mqtt_host: str
    mqtt_port: int

    # QuestDB
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str

    # FastAPI
    app_host: str
    app_port: int

    # Tell pydantic-settings to load from the .env file in this directory
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# Single instance — import this everywhere instead of re-reading .env each time
settings = Settings()
