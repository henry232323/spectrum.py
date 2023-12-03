import dataclasses


@dataclasses.dataclass
class Block:
    key: str
    text: str
    type: str
    depth: int
    inlineStyleRanges: list
    entityRanges: list
    data: list


@dataclasses.dataclass
class ContentState:
    blocks: list[Block]
    entityMap: list

    def __post_init__(self):
        self.blocks = [Block(**block) for block in self.blocks]


@dataclasses.dataclass
class ContentBlock:
    id: int
    type: str
    blocks: list[Block]

    def __post_init__(self):
        self.id = int(self.id)
        self.blocks = [Block(**block) for block in self.blocks]
