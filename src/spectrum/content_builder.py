"""
ContentBuilder — fluent API for composing Spectrum forum/message content.

Usage:
    content = (ContentBuilder()
        .text("Hey everyone,")
        .blank()
        .bold("I built ")
        .link("sc-orgs.space", "https://sc-orgs.space", bold=True)
        .text(" is awesome.")
        .blank()
        .heading("What it does:")
        .bullet("Search and filter orgs")
        .bullet("Browse events")
        .image("upload:3460462")
        .text("o7")
    )

    # Use with create_thread:
    thread = await channel.create_thread(
        subject="My post",
        plaintext=content.plaintext,
        content_blocks=content.content_blocks,
    )
"""

from __future__ import annotations

import random
import string
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .models.upload import Upload


def _generate_key() -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=5))


def _generate_block_id() -> str:
    part1 = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    part2 = "".join(random.choices(string.ascii_lowercase + string.digits, k=13))
    return f"{part1}-{part2}"


class BlockType(str, Enum):
    UNSTYLED = "unstyled"
    HEADER_ONE = "header-one"
    HEADER_TWO = "header-two"
    HEADER_THREE = "header-three"
    UNORDERED_LIST = "unordered-list-item"
    ORDERED_LIST = "ordered-list-item"
    BLOCKQUOTE = "blockquote"
    CODE_BLOCK = "code-block"


@dataclass
class _InlineStyle:
    offset: int
    length: int
    style: str


@dataclass
class _EntityRange:
    offset: int
    length: int
    key: int


@dataclass
class _Entity:
    type: str
    mutability: str
    data: dict


@dataclass
class _TextBlock:
    text: str
    type: BlockType = BlockType.UNSTYLED
    depth: int = 0
    inline_styles: list[_InlineStyle] = field(default_factory=list)
    entity_ranges: list[_EntityRange] = field(default_factory=list)


@dataclass
class _TextSection:
    blocks: list[_TextBlock] = field(default_factory=list)
    entities: dict[int, _Entity] = field(default_factory=dict)
    _next_entity_key: int = 0

    def add_entity(self, entity: _Entity) -> int:
        key = self._next_entity_key
        self.entities[key] = entity
        self._next_entity_key += 1
        return key


@dataclass
class _ImageSection:
    upload_ids: list[str]


class ContentBuilder:
    """Fluent builder for Spectrum content_blocks."""

    def __init__(self):
        self._sections: list[_TextSection | _ImageSection] = []
        self._current_text: Optional[_TextSection] = None
        self._pending_styles: list[tuple[str, Optional[str]]] = []

    def _ensure_text_section(self) -> _TextSection:
        if self._current_text is None:
            self._current_text = _TextSection()
            self._sections.append(self._current_text)
        return self._current_text

    def _flush_text(self):
        self._current_text = None

    # --- Text content ---

    def text(self, content: str) -> "ContentBuilder":
        """Add unstyled text. Newlines create separate blocks."""
        section = self._ensure_text_section()
        lines = content.split("\n")
        for line in lines:
            section.blocks.append(_TextBlock(text=line))
        return self

    def bold(self, content: str) -> "ContentBuilder":
        """Add a new block with bold text. To inline bold within a line, use append_bold()."""
        section = self._ensure_text_section()
        block = _TextBlock(text=content)
        block.inline_styles.append(_InlineStyle(offset=0, length=len(content), style="BOLD"))
        section.blocks.append(block)
        return self

    def append_bold(self, content: str) -> "ContentBuilder":
        """Append bold text to the current line."""
        section = self._ensure_text_section()
        if not section.blocks:
            section.blocks.append(_TextBlock(text=""))
        block = section.blocks[-1]
        offset = len(block.text)
        block.text += content
        block.inline_styles.append(_InlineStyle(offset=offset, length=len(content), style="BOLD"))
        return self

    def italic(self, content: str) -> "ContentBuilder":
        """Add a new block with italic text. To inline italic within a line, use append_italic()."""
        section = self._ensure_text_section()
        block = _TextBlock(text=content)
        block.inline_styles.append(_InlineStyle(offset=0, length=len(content), style="ITALIC"))
        section.blocks.append(block)
        return self

    def append_italic(self, content: str) -> "ContentBuilder":
        """Append italic text to the current line."""
        section = self._ensure_text_section()
        if not section.blocks:
            section.blocks.append(_TextBlock(text=""))
        block = section.blocks[-1]
        offset = len(block.text)
        block.text += content
        block.inline_styles.append(_InlineStyle(offset=offset, length=len(content), style="ITALIC"))
        return self

    def link(self, display_text: str, href: str, bold: bool = False) -> "ContentBuilder":
        """Add a hyperlink. Optionally bold."""
        section = self._ensure_text_section()
        if not section.blocks:
            section.blocks.append(_TextBlock(text=""))
        block = section.blocks[-1]
        offset = len(block.text)
        block.text += display_text
        entity_key = section.add_entity(_Entity(
            type="LINK",
            mutability="MUTABLE",
            data={"href": href}
        ))
        block.entity_ranges.append(_EntityRange(offset=offset, length=len(display_text), key=entity_key))
        if bold:
            block.inline_styles.append(_InlineStyle(offset=offset, length=len(display_text), style="BOLD"))
        return self

    def append(self, content: str) -> "ContentBuilder":
        """Append plain text to the current line without creating a new block."""
        section = self._ensure_text_section()
        if not section.blocks:
            section.blocks.append(_TextBlock(text=""))
        section.blocks[-1].text += content
        return self

    # --- Block-level elements ---

    def blank(self) -> "ContentBuilder":
        """Add an empty line."""
        section = self._ensure_text_section()
        section.blocks.append(_TextBlock(text=""))
        return self

    def heading(self, content: str, level: int = 1) -> "ContentBuilder":
        """Add a heading (level 1-3)."""
        types = {1: BlockType.HEADER_ONE, 2: BlockType.HEADER_TWO, 3: BlockType.HEADER_THREE}
        section = self._ensure_text_section()
        section.blocks.append(_TextBlock(text=content, type=types.get(level, BlockType.HEADER_ONE)))
        return self

    def bullet(self, content: str) -> "ContentBuilder":
        """Add an unordered list item."""
        section = self._ensure_text_section()
        section.blocks.append(_TextBlock(text=content, type=BlockType.UNORDERED_LIST))
        return self

    def numbered(self, content: str) -> "ContentBuilder":
        """Add an ordered list item."""
        section = self._ensure_text_section()
        section.blocks.append(_TextBlock(text=content, type=BlockType.ORDERED_LIST))
        return self

    def quote(self, content: str) -> "ContentBuilder":
        """Add a blockquote."""
        section = self._ensure_text_section()
        section.blocks.append(_TextBlock(text=content, type=BlockType.BLOCKQUOTE))
        return self

    def code(self, content: str) -> "ContentBuilder":
        """Add a code block."""
        section = self._ensure_text_section()
        for line in content.split("\n"):
            section.blocks.append(_TextBlock(text=line, type=BlockType.CODE_BLOCK))
        return self

    # --- Media ---

    def image(self, *uploads: "Upload | str") -> "ContentBuilder":
        """Add one or more images. Pass Upload objects from upload_image() or string IDs."""
        self._flush_text()
        for upload in uploads:
            uid = upload.id if hasattr(upload, 'id') else str(upload)
            self._sections.append(_ImageSection(upload_ids=[uid]))
        return self

    # --- Output ---

    @property
    def plaintext(self) -> str:
        """Generate plaintext representation of the content."""
        parts = []
        for section in self._sections:
            if isinstance(section, _TextSection):
                for block in section.blocks:
                    parts.append(block.text)
        return "\n".join(parts)

    @property
    def content_blocks(self) -> list[dict]:
        """Generate the content_blocks payload for the Spectrum API."""
        blocks = []
        text_counter = 0
        for section in self._sections:
            if isinstance(section, _ImageSection):
                for uid in section.upload_ids:
                    blocks.append({
                        "id": _generate_block_id(),
                        "type": "image",
                        "data": [uid],
                    })
            elif isinstance(section, _TextSection):
                text_counter += 1
                draft_blocks = []
                for tb in section.blocks:
                    draft_blocks.append({
                        "key": _generate_key(),
                        "text": tb.text,
                        "type": tb.type.value,
                        "depth": tb.depth,
                        "inlineStyleRanges": [
                            {"offset": s.offset, "length": s.length, "style": s.style}
                            for s in tb.inline_styles
                        ],
                        "entityRanges": [
                            {"offset": er.offset, "length": er.length, "key": er.key}
                            for er in tb.entity_ranges
                        ],
                        "data": {},
                    })

                entity_map = {}
                for key, entity in section.entities.items():
                    entity_map[str(key)] = {
                        "type": entity.type,
                        "mutability": entity.mutability,
                        "data": entity.data,
                    }

                blocks.append({
                    "id": text_counter,
                    "type": "text",
                    "data": {
                        "blocks": draft_blocks,
                        "entityMap": entity_map,
                    },
                })

        return blocks

    def build(self) -> dict:
        """Return a dict with both content_blocks and plaintext, ready to unpack into create_thread."""
        return {
            "content_blocks": self.content_blocks,
            "plaintext": self.plaintext,
        }
