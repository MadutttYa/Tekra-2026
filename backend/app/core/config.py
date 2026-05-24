from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    mqtt_host: str
    mqtt_port: int

    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str

    app_host: str
    app_port: int

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
