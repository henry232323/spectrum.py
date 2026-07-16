from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import aiohttp

ROADMAP_BASE_URL = "https://robertsspaceindustries.com/api/roadmap/v1"


@dataclass
class Board:
    id: int = 0
    name: str = ""
    description: str = ""
    slug: str = ""
    url: str = ""
    released: bool = False
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        # Handle nested or extra fields gracefully
        pass


@dataclass
class Category:
    id: int = 0
    board_id: int = 0
    name: str = ""
    slug: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclass
class Release:
    id: int = 0
    board_id: int = 0
    name: str = ""
    description: str = ""
    slug: str = ""
    url: str = ""
    released: bool = False
    release_date: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclass
class RoadmapCard:
    id: int = 0
    board_id: int = 0
    category_id: int = 0
    release_id: int = 0
    name: str = ""
    description: str = ""
    status: str = ""
    thumbnail: str = ""
    url: str = ""
    released: bool = False
    created_at: str = ""
    updated_at: str = ""
    tasks: int = 0
    completed: int = 0
    inboard_id: Optional[int] = None


class RoadmapClient:
    """Client for the RSI Roadmap REST API.

    All endpoints are public GET requests returning JSON.
    No authentication required.
    """

    def __init__(self):
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        """Close the underlying HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _get(self, path: str, params: dict | None = None) -> dict | list:
        session = await self._get_session()
        url = f"{ROADMAP_BASE_URL}{path}"
        async with session.get(url, params=params) as resp:
            resp.raise_for_status()
            return await resp.json(content_type=None)

    # --- Boards ---

    async def fetch_boards(self) -> list[Board]:
        """Fetch all roadmap boards.

        Board 1 = Release View, Board 2 = Squadron 42.
        """
        data = await self._get("/boards")
        if isinstance(data, dict):
            data = data.get("data", data.get("boards", []))
        return [Board(**self._extract_board(item)) for item in data]

    async def fetch_board(self, board_id: int) -> Board:
        """Fetch a single roadmap board by ID."""
        data = await self._get(f"/boards/{board_id}")
        if isinstance(data, dict) and "data" in data:
            data = data["data"]
        return Board(**self._extract_board(data))

    # --- Categories ---

    async def fetch_categories(self, board_id: int = 1) -> list[Category]:
        """Fetch card categories for a given board.

        Categories include: AI, Characters, Core Tech, Gameplay,
        Locations, Missions, Ships, Weapons.
        """
        data = await self._get("/categories", params={"board_id": board_id})
        if isinstance(data, dict):
            data = data.get("data", data.get("categories", []))
        return [Category(**self._extract_category(item)) for item in data]

    # --- Cards ---

    async def fetch_cards(self, board_id: int = 1) -> list[RoadmapCard]:
        """Fetch all roadmap cards for a given board.

        Returns card name, description, release_id, category_id,
        status (Committed/Tentative), thumbnail URLs, and timestamps.
        """
        data = await self._get("/cards", params={"board_id": board_id})
        if isinstance(data, dict):
            data = data.get("data", data.get("cards", []))
        return [RoadmapCard(**self._extract_card(item)) for item in data]

    # --- Releases ---

    async def fetch_releases(self, board_id: int = 1) -> list[Release]:
        """Fetch all release versions for a given board.

        Returns version slugs, release dates, descriptions, and status.
        """
        data = await self._get("/releases", params={"board_id": board_id})
        if isinstance(data, dict):
            data = data.get("data", data.get("releases", []))
        return [Release(**self._extract_release(item)) for item in data]

    # --- Field extraction helpers ---

    @staticmethod
    def _extract_board(raw: dict) -> dict:
        """Extract known Board fields from a raw API response dict."""
        return {
            "id": raw.get("id", 0),
            "name": raw.get("name", ""),
            "description": raw.get("description", ""),
            "slug": raw.get("slug", ""),
            "url": raw.get("url", ""),
            "released": raw.get("released", False),
            "created_at": raw.get("created_at", ""),
            "updated_at": raw.get("updated_at", ""),
        }

    @staticmethod
    def _extract_category(raw: dict) -> dict:
        """Extract known Category fields from a raw API response dict."""
        return {
            "id": raw.get("id", 0),
            "board_id": raw.get("board_id", 0),
            "name": raw.get("name", ""),
            "slug": raw.get("slug", ""),
            "created_at": raw.get("created_at", ""),
            "updated_at": raw.get("updated_at", ""),
        }

    @staticmethod
    def _extract_card(raw: dict) -> dict:
        """Extract known RoadmapCard fields from a raw API response dict."""
        return {
            "id": raw.get("id", 0),
            "board_id": raw.get("board_id", 0),
            "category_id": raw.get("category_id", 0),
            "release_id": raw.get("release_id", 0),
            "name": raw.get("name", ""),
            "description": raw.get("description", ""),
            "status": raw.get("status", ""),
            "thumbnail": raw.get("thumbnail", ""),
            "url": raw.get("url", ""),
            "released": raw.get("released", False),
            "created_at": raw.get("created_at", ""),
            "updated_at": raw.get("updated_at", ""),
            "tasks": raw.get("tasks", 0),
            "completed": raw.get("completed", 0),
            "inboard_id": raw.get("inboard_id"),
        }

    @staticmethod
    def _extract_release(raw: dict) -> dict:
        """Extract known Release fields from a raw API response dict."""
        return {
            "id": raw.get("id", 0),
            "board_id": raw.get("board_id", 0),
            "name": raw.get("name", ""),
            "description": raw.get("description", ""),
            "slug": raw.get("slug", ""),
            "url": raw.get("url", ""),
            "released": raw.get("released", False),
            "release_date": raw.get("release_date", ""),
            "created_at": raw.get("created_at", ""),
            "updated_at": raw.get("updated_at", ""),
        }
