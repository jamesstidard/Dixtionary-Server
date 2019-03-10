import os

from sanic_envconfig import EnvConfig


class Config(EnvConfig):
    DEBUG: bool = False
    PORT: int = 8002
    WORKERS: int = os.cpu_count() or 1

    DATABASE_URL: str
