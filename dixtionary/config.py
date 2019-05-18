import secrets
import multiprocessing

from sanic_envconfig import EnvConfig


class Config(EnvConfig):
    DEBUG: bool = False
    PORT: int = 8000
    WORKERS: int = multiprocessing.cpu_count()
    SECRET: str = secrets.token_hex(64)
    REDIS_URL: str = "redis://localhost"
