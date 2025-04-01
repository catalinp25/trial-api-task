from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    API_KEY: str = "API_KEY"
    API_KEY_HEADER: str = "X-API-Key"
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"
    DATABASE_URL: str = ""
    POSTGRES_DB: str = "postgres"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    
    
    # Blockchain settings
    BITTENSOR_NETWORK: str ="testnet"
    BITTENSOR_WALLET_NAME: str = "default"
    BITTENSOR_WALLET_HOTKEY: str = "default"
    DEFAULT_NETUID: int =18
    DEFAULT_HOTKEY: str =  ""

    WALLET_SEED_PHRASE: str = ""
    
    # API keys for external services
    DATURA_API_KEY: str = ""
    CHUTES_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = ""
    
    # Caching settings
    CACHE_TTL: int = 120  # Cache TTL in seconds

    model_config = {
        "env_file": ".env",
        "case_sensitive": True
    }


settings = Settings()