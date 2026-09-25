from functools import lru_cache
from pathlib import Path
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

class Settings(BaseSettings):
    app_name: str = 'ConceptBridge API'
    app_env: str = 'development'
    api_prefix: str = '/api/v1'
    jwt_secret_key: str = 'change-this-development-secret-key'
    access_token_expire_minutes: int = 60 * 24
    mysql_host: str = '127.0.0.1'
    mysql_port: int = 3306
    mysql_user: str = 'root'
    mysql_password: str = ''
    mysql_database: str = 'conceptbridge'
    default_provider: str = 'auto'
    auto_provider_order: str = 'gemini,openai,anthropic'
    enable_mock: bool = True
    provider_timeout_seconds: float = Field(default=25, ge=1, le=60)
    max_output_tokens: int = Field(default=1600, ge=128, le=8000)
    context_max_bytes: int = Field(default=26000, ge=8000, le=100000)
    recent_message_count: int = Field(default=8, ge=2, le=20)
    storage_dir: Path = Path('storage')
    allowed_origins: str = 'http://localhost:3000,http://127.0.0.1:3000'
    jwt_secret_key: str = 'change-this-conceptbridge-secret-key'
    jwt_algorithm: str = 'HS256'
    jwt_expire_minutes: int = 60 * 24 * 7
    openai_api_key: str | None = None
    openai_model: str = 'gpt-5.6-luna'
    gemini_api_key: str | None = None
    gemini_model: str = 'gemini-3.7-flash'
    anthropic_api_key: str | None = None
    anthropic_model: str = 'claude-sonnet-5'
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')
    youtube_api_key: str | None = None
    @model_validator(mode='after')
    def validate_providers(self):
        real = {'gemini', 'openai', 'anthropic'}
        if self.default_provider not in real | {'auto', 'mock'}:
            raise ValueError('Invalid DEFAULT_PROVIDER')
        if not self.provider_order or any(p not in real for p in self.provider_order):
            raise ValueError('AUTO_PROVIDER_ORDER must contain only real providers; mock is explicit development mode')
        if len(self.provider_order) != len(set(self.provider_order)):
            raise ValueError('AUTO_PROVIDER_ORDER must not repeat providers')
        if self.default_provider == 'mock' and not self.enable_mock:
            raise ValueError('DEFAULT_PROVIDER=mock requires ENABLE_MOCK=true')
        return self

    @property
    def database_url(self) -> URL:
        return URL.create('mysql+pymysql', username=self.mysql_user, password=self.mysql_password,
                          host=self.mysql_host, port=self.mysql_port, database=self.mysql_database,
                          query={'charset': 'utf8mb4'})
    @property
    def provider_order(self) -> list[str]:
        return [p.strip() for p in self.auto_provider_order.split(',') if p.strip()]

@lru_cache
def get_settings() -> Settings:
    return Settings()
