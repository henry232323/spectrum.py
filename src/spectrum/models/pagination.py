import dataclasses
from typing import TypeVar, Generic

T = TypeVar('T')


@dataclasses.dataclass
class PaginatedResult(Generic[T]):
    items: list[T]
    total: int
    page: int
    pages_total: int

    def __iter__(self):
        return iter(self.items)

    def __len__(self):
        return len(self.items)

    @property
    def has_next(self) -> bool:
        return self.page < self.pages_total
