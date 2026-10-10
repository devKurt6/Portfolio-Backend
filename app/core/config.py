from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    database_url: str = 'sqlite:///./data/portfolio.db'
    allowed_origins: str = 'http://localhost:4173,http://127.0.0.1:4173'
    preview_origin_regex: str | None = None
    admin_token: str = Field(min_length=32)
    ip_hash_salt: str = Field(min_length=32)
    wall_post_seconds: int = Field(default=15, ge=1)
    wall_daily_cap: int = Field(default=30, ge=1)
    wall_report_threshold: int = Field(default=3, ge=1)
    enable_chat_logs: bool = False
    llm_enabled: bool = False
    llm_api_key: str = ''
    llm_model: str = ''
    max_body_bytes: int = Field(default=16384, ge=1024)

    @model_validator(mode='after')
    def secure_configuration(self):
        if '*' in self.allowed_origins or any(x.startswith(('CHANGE', 'PLACEHOLDER')) for x in (self.admin_token, self.ip_hash_salt)):
            raise ValueError('Set real secrets and explicit CORS origins.')
        if self.llm_enabled:
            raise ValueError('No LLM provider installed; keep LLM_ENABLED=false.')
        return self
