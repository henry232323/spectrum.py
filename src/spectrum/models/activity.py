import dataclasses
from datetime import datetime

from spectrum.util.datetime import parse_timestamp


@dataclasses.dataclass
class Activity:
    time_created: datetime
    highlight_role_id: int
    member_id: int = None
    member: dict = None

    def __post_init__(self):
        self.member_id = self.member_id or int(self.member['id'])
        self.highlight_role_id = int(self.highlight_role_id) if self.highlight_role_id else None
        self.time_created = parse_timestamp(self.time_created)
