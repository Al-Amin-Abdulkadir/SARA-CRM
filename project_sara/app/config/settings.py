from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name : str = "SARA CRM"
    debug : bool = True
    database_url : str ="postgresql://alamin@localhost:5432/sara_crm"
    secret_key : str = "change-me-in-production"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()

