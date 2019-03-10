from sanic_envconfig import EnvConfig


class Config(EnvConfig):
    DEBUG: bool = False
    PORT: int = 8000
    WORKERS: int = 1

    DATABASE_URL: str
