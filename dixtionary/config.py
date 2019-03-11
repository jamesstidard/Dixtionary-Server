import secrets
import multiprocessing

from sanic_envconfig import EnvConfig


class Config(EnvConfig):
    DEBUG: bool = False
    PORT: int = 8000
    WORKERS: int = multiprocessing.cpu_count()
    COOKIE_SECRET: str = secrets.token_hex(64)
    DATABASE_URL: str = 'redis://localhost'
