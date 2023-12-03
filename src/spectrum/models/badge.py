import dataclasses
from typing import Optional


@dataclasses.dataclass
class Badge:
    name: str
    icon: str
    url: Optional[str] = None
