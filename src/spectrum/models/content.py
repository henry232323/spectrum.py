import dataclasses
from datetime import datetime
from typing import Optional


@dataclasses.dataclass
class EntityMap:
    type: str
    mutability: str
    data: dict


@dataclasses.dataclass
class EntityRange:
    offset: int
    length: int
    key: int


@dataclasses.dataclass
class InlineStyleRange:
    offset: int
    length: int
    style: str


@dataclasses.dataclass
class Block:
    key: str
    text: str
    type: str
    depth: int
    inlineStyleRanges: list[InlineStyleRange]
    entityRanges: list[EntityRange]
    data: list

    def __post_init__(self):
        self.entityRanges = [EntityRange(**er) for er in self.entityRanges]
        self.inlineStyleRanges = [InlineStyleRange(**isr) for isr in self.inlineStyleRanges]


@dataclasses.dataclass
class ContentState:
    blocks: list[Block]
    entityMap: list[EntityMap]

    def __post_init__(self):
        self.blocks = [Block(**block) for block in self.blocks]
        self.entityMap = [EntityMap(**em) for em in self.entityMap]


@dataclasses.dataclass
class ContentBlock:
    id: int
    type: str
    blocks: list[Block]

    def __post_init__(self):
        self.id = int(self.id)
        self.blocks = [Block(**block) for block in self.blocks]


@dataclasses.dataclass
class ImageSizeData:
    url: str
    image_width: int
    image_height: int


@dataclasses.dataclass
class Embed:
    embed_type: str
    url: str
    provider_name: str
    title: str
    description: str
    image: str
    image_width: int
    image_height: int
    time_fetched: datetime
    sizes: dict[str, ImageSizeData]
    provider_icon: Optional[str] = None
    embed_code: Optional[str] = None
    embed_width: Optional[int] = None
    embed_height: Optional[int] = None
    gifv: Optional = None

    def __post_init__(self):
        self.time_fetched = datetime.utcfromtimestamp(self.time_fetched)
        self.sizes = {k: ImageSizeData(**v) for k, v in self.sizes.items()}


@dataclasses.dataclass
class Media:
    id: str
    slug: str
    type: str
    data: Embed

    def __post_init__(self):
        if self.type == "embed":
            self.data = Embed(**self.data)
