from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import aiohttp

STARMAP_BASE_URL = "https://robertsspaceindustries.com/api/starmap"


@dataclass
class StarSystem:
    id: int = 0
    code: str = ""
    name: str = ""
    position_x: float = 0.0
    position_y: float = 0.0
    position_z: float = 0.0
    type: str = ""
    affiliation: list[dict] = field(default_factory=list)
    size: float = 0.0
    population: float = 0.0
    economy: float = 0.0
    danger: float = 0.0
    status: str = ""
    description: str = ""
    info_url: str = ""
    thumbnail: Optional[dict] = None


@dataclass
class CelestialObject:
    id: int = 0
    code: str = ""
    name: str = ""
    designation: str = ""
    type: str = ""
    subtype: str = ""
    description: str = ""
    affiliation: list[dict] = field(default_factory=list)
    habitable: bool = False
    fairchanceact: bool = False
    size: float = 0.0
    parent_id: Optional[int] = None
    star_system_id: Optional[int] = None
    star_system: Optional[StarSystem] = None
    children: list[CelestialObject] = field(default_factory=list)
    texture: Optional[dict] = None
    shader_data: Optional[dict] = None
    info_url: str = ""
    thumbnail: Optional[dict] = None

    def __post_init__(self):
        if isinstance(self.star_system, dict):
            self.star_system = StarSystem(**self.star_system)
        self.children = [
            CelestialObject(**c) if isinstance(c, dict) else c
            for c in self.children
        ]


@dataclass
class Species:
    id: int = 0
    code: str = ""
    name: str = ""


@dataclass
class Affiliation:
    id: int = 0
    code: str = ""
    color: str = ""
    name: str = ""


class StarmapClient:
    """Client for the RSI Starmap REST API (star systems, celestial objects, species, factions)."""

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

    async def _post(self, path: str, body: dict | None = None) -> Any:
        """Execute a POST request against the starmap API and return the data payload."""
        session = await self._get_session()
        url = f"{STARMAP_BASE_URL}/{path.lstrip('/')}"
        async with session.post(
            url,
            json=body or {},
            headers={"content-type": "application/json", "accept": "application/json"},
        ) as resp:
            result = await resp.json(content_type=None)
            if not result.get("success"):
                raise RuntimeError(f"Starmap API error: {result}")
            return result.get("data")

    # --- Endpoints ---

    async def bootup(self) -> dict:
        """Full initialization payload (config + all systems).

        Returns the raw data dict containing systems, species, affiliations,
        tunnels, and config.
        """
        return await self._post("bootup")

    async def star_systems(self) -> list[StarSystem]:
        """Fetch all star systems (~90).

        Returns a list of StarSystem dataclass instances.
        """
        data = await self._post("star-systems")
        resultset = data.get("resultset", []) if isinstance(data, dict) else data
        valid_fields = {f.name for f in StarSystem.__dataclass_fields__.values()}
        return [StarSystem(**{k: v for k, v in s.items() if k in valid_fields}) for s in resultset]

    async def find(self, query: str) -> dict:
        """Search star systems and objects by name.

        Args:
            query: Search term (e.g. "stanton").

        Returns the raw data dict with matching systems and objects.
        """
        return await self._post("find", {"query": query})

    async def species(self) -> list[Species]:
        """Fetch all species (~6).

        Returns a list of Species dataclass instances.
        """
        data = await self._post("species")
        resultset = data.get("resultset", []) if isinstance(data, dict) else data
        return [Species(**s) for s in resultset]

    async def affiliations(self) -> list[Affiliation]:
        """Fetch all affiliations/factions (~6).

        Returns a list of Affiliation dataclass instances.
        """
        data = await self._post("affiliations")
        resultset = data.get("resultset", []) if isinstance(data, dict) else data
        return [Affiliation(**a) for a in resultset]

    async def celestial_object(self, code: str) -> CelestialObject:
        """Fetch details for a celestial object by its code.

        Args:
            code: The object code (e.g. "STANTON.PLANETS.STANTONIHURSTONDYNAMICS").

        Returns a CelestialObject dataclass instance.
        """
        data = await self._post(f"celestial-objects/{code}")
        obj_data = data.get("resultset", [data]) if isinstance(data, dict) else [data]
        # API returns a single object in resultset or directly
        if isinstance(obj_data, list) and len(obj_data) > 0:
            return CelestialObject(**obj_data[0])
        return CelestialObject(**obj_data) if isinstance(obj_data, dict) else CelestialObject()
