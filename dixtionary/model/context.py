from typing import Optional
from dataclasses import dataclass


@dataclass
class Context:
    state: dict
    current_user: Optional[dict] = None
