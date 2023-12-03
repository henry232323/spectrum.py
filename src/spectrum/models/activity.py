import dataclasses
from datetime import datetime


@dataclasses.dataclass
class Activity:
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.member_id = int(kwargs['member']['id'])

    time_created: datetime
    member_id: int
    highlight_role_id: int

    def __post_init__(self):
        self.highlight_role_id = int(self.highlight_role_id)
        self.time_created = datetime.utcfromtimestamp(self.time_created)
