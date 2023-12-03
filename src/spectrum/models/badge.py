import dataclasses


@dataclasses.dataclass
class Badge:
    name: str
    icon: str
    url: str | None
