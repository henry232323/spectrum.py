from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import aiohttp

RSI_API_BASE = "https://robertsspaceindustries.com/api"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


@dataclass
class CrowdfundStats:
    """Crowdfunding stats from /api/stats/getCrowdfundStats."""

    fans: int = 0
    funds: int = 0
    chart: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class LeaderboardEntry:
    """A single entry in a leaderboard result."""

    rank: int = 0
    nickname: str = ""
    score: int = 0
    wins: int = 0
    losses: int = 0
    kills: int = 0
    deaths: int = 0
    assists: int = 0
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ShipHoloview:
    """3D ship data from /api/holoviewer/getShip."""

    id: str = ""
    name: str = ""
    manufacturer: str = ""
    propulsion: list[dict[str, Any]] = field(default_factory=list)
    thrusters: list[dict[str, Any]] = field(default_factory=list)
    weapons: list[dict[str, Any]] = field(default_factory=list)
    modular: list[dict[str, Any]] = field(default_factory=list)
    avionics: list[dict[str, Any]] = field(default_factory=list)
    poi: list[dict[str, Any]] = field(default_factory=list)
    offsets: dict[str, Any] = field(default_factory=dict)
    rotations: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class CommLinkSeries:
    """A series entry from /api/hub/getSeries."""

    id: str = ""
    name: str = ""
    status: str = ""
    title: str = ""
    url: str = ""


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class RSIClient:
    """Client for miscellaneous RSI REST APIs (stats, leaderboards, holoviewer, hub/news, store, account).

    All endpoints are POST to https://robertsspaceindustries.com/api/ with JSON body.
    Most do not require authentication. Pass ``rsi_token`` for auth-required endpoints.
    """

    def __init__(self, rsi_token: str | None = None):
        self._rsi_token = rsi_token
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        """Close the underlying HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _post(self, path: str, body: dict[str, Any] | None = None, auth: bool = False) -> Any:
        """POST to RSI API and return the ``data`` field from the response."""
        session = await self._get_session()
        url = f"{RSI_API_BASE}/{path.lstrip('/')}"
        headers: dict[str, str] = {"content-type": "application/json"}
        if auth and self._rsi_token:
            headers["x-rsi-token"] = self._rsi_token
        async with session.post(url, json=body or {}, headers=headers) as resp:
            result = await resp.json(content_type=None)
            if not result.get("success"):
                msg = result.get("msg") or result.get("message") or str(result)
                raise RuntimeError(f"RSI API error ({path}): {msg}")
            return result.get("data")

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    async def get_crowdfund_stats(
        self,
        *,
        chart: str = "day",
        fans: bool = True,
        funds: bool = True,
    ) -> CrowdfundStats:
        """Fetch crowdfunding statistics (citizen count, total funding, daily chart).

        Parameters
        ----------
        chart : str
            Chart granularity, e.g. ``"day"``.
        fans : bool
            Include citizen count.
        funds : bool
            Include total funding (in cents).
        """
        data = await self._post("stats/getCrowdfundStats", {
            "chart": chart,
            "fans": fans,
            "funds": funds,
        })
        return CrowdfundStats(
            fans=data.get("fans", 0),
            funds=data.get("funds", 0),
            chart=data.get("chart", []),
        )

    # ------------------------------------------------------------------
    # Leaderboards
    # ------------------------------------------------------------------

    async def get_leaderboard(
        self,
        *,
        mode: str = "BR",
        page: int = 1,
        pagesize: int = 10,
    ) -> list[LeaderboardEntry]:
        """Fetch a leaderboard page.

        Parameters
        ----------
        mode : str
            Game mode: ``"BR"`` (Battle Royale), ``"SB"`` (Squadron Battle),
            ``"PS"`` (Pirate Swarm).
        page : int
            Page number (1-indexed).
        pagesize : int
            Number of entries per page.
        """
        data = await self._post("leaderboards/getLeaderboard", {
            "mode": mode,
            "page": page,
            "pagesize": pagesize,
        })
        entries: list[LeaderboardEntry] = []
        for item in (data if isinstance(data, list) else data.get("resultset", [])):
            entries.append(LeaderboardEntry(
                rank=int(item.get("rank", 0)),
                nickname=item.get("nickname", ""),
                score=int(item.get("score", 0)),
                wins=int(item.get("wins", 0)),
                losses=int(item.get("losses", 0)),
                kills=int(item.get("kills", 0)),
                deaths=int(item.get("deaths", 0)),
                assists=int(item.get("assists", 0)),
                raw=item,
            ))
        return entries

    async def get_leaderboard_overview(self) -> dict[str, Any]:
        """Fetch leaderboard overview (top players across all modes).

        Returns the raw data dict from the API.
        """
        data = await self._post("leaderboards/getOverview", {})
        return data if isinstance(data, dict) else {}

    # ------------------------------------------------------------------
    # Holoviewer (3D ship data)
    # ------------------------------------------------------------------

    async def get_ship_holoview(self, ship_id: str) -> ShipHoloview:
        """Fetch 3D model/component data for a ship.

        Parameters
        ----------
        ship_id : str
            The ship ID (numeric string).
        """
        data = await self._post("holoviewer/getShip", {"ship_id": ship_id})
        return ShipHoloview(
            id=str(data.get("id", "")),
            name=data.get("name", ""),
            manufacturer=data.get("manufacturer", ""),
            propulsion=data.get("propulsion", []),
            thrusters=data.get("thrusters", []),
            weapons=data.get("weapons", []),
            modular=data.get("modular", []),
            avionics=data.get("avionics", []),
            poi=data.get("poi", []),
            offsets=data.get("offsets", {}),
            rotations=data.get("rotations", {}),
            raw=data,
        )

    # ------------------------------------------------------------------
    # Hub / News
    # ------------------------------------------------------------------

    async def get_comm_link_items(
        self,
        *,
        page: int = 1,
        pagesize: int = 10,
    ) -> dict[str, Any]:
        """Fetch Comm-Link news items (HTML blocks).

        Parameters
        ----------
        page : int
            Page number (1-indexed).
        pagesize : int
            Items per page.

        Returns
        -------
        dict
            Raw response data containing HTML news blocks.
        """
        data = await self._post("hub/getCommlinkItems", {
            "page": page,
            "pagesize": pagesize,
        })
        return data if isinstance(data, dict) else {"items": data}

    async def get_series(self) -> list[CommLinkSeries]:
        """Fetch all Comm-Link series."""
        data = await self._post("hub/getSeries", {})
        series_list: list[CommLinkSeries] = []
        items = data if isinstance(data, list) else data.get("series", [])
        for item in items:
            series_list.append(CommLinkSeries(
                id=str(item.get("id", "")),
                name=item.get("name", ""),
                status=item.get("status", ""),
                title=item.get("title", ""),
                url=item.get("url", ""),
            ))
        return series_list

    # ------------------------------------------------------------------
    # Store (basic REST, not GraphQL)
    # ------------------------------------------------------------------

    async def get_ships(
        self,
        *,
        page: int = 1,
        pagesize: int = 20,
    ) -> dict[str, Any]:
        """Fetch ships from the store (HTML + totalrows).

        Parameters
        ----------
        page : int
            Page number (1-indexed).
        pagesize : int
            Ships per page.

        Returns
        -------
        dict
            Contains HTML ship data and ``totalrows`` count.
        """
        data = await self._post("store/getShips", {
            "page": page,
            "pagesize": pagesize,
        })
        return data if isinstance(data, dict) else {}

    async def search_store(
        self,
        *,
        sort: str = "price_asc",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Search the RSI store.

        Parameters
        ----------
        sort : str
            Sort order, e.g. ``"price_asc"``, ``"price_desc"``.
        **kwargs
            Additional search parameters passed in the body.
        """
        body: dict[str, Any] = {"isotope_sort": sort}
        body.update(kwargs)
        data = await self._post("store/searchStore", body)
        return data if isinstance(data, dict) else {}

    # ------------------------------------------------------------------
    # Account (auth required)
    # ------------------------------------------------------------------

    async def set_auth_token(self) -> dict[str, Any]:
        """Exchange RSI token for a JWT (requires ``rsi_token``).

        Returns
        -------
        dict
            Contains the JWT token data for downstream services.
        """
        if not self._rsi_token:
            raise ValueError("rsi_token is required for set_auth_token")
        data = await self._post("account/v2/setAuthToken", {}, auth=True)
        return data if isinstance(data, dict) else {}

    async def check_nickname_availability(self, nickname: str) -> bool:
        """Check if a nickname is available (no auth required).

        Parameters
        ----------
        nickname : str
            The nickname to check.

        Returns
        -------
        bool
            True if the nickname is available, False otherwise.
        """
        data = await self._post("account/checkNicknameAvailability", {"nickname": nickname})
        return bool(data)
