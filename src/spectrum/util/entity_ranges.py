import re
from typing import List

from spectrum.models.content import EntityRange

url_pattern = re.compile(
    r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)")


def get_entity_ranges(url: str) -> List[EntityRange]:
    ranges = []
    for i, match in enumerate(url_pattern.finditer(url)):
        ranges.append(EntityRange(match.start(), match.end() - match.start(), i))

    return ranges
