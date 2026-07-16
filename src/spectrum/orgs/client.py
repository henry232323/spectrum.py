from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

import aiohttp

RSI_BASE = "https://robertsspaceindustries.com"


@dataclass
class Org:
    name: str = ""
    symbol: str = ""
    model: str = ""
    icon: str = ""
    avatar: str = ""
    archetype: str = ""
    language: str = ""
    commitment: str = ""
    recruiting: bool = False
    roleplay: bool = False
    member_count: int = 0
    href: str = ""

    @property
    def url(self) -> str:
        return f"{RSI_BASE}/orgs/{self.symbol}" if self.symbol else ""

    @property
    def icon_url(self) -> str:
        if self.icon and not self.icon.startswith("http"):
            return f"{RSI_BASE}{self.icon}"
        return self.icon

    @property
    def avatar_url(self) -> str:
        if self.avatar and not self.avatar.startswith("http"):
            return f"{RSI_BASE}{self.avatar}"
        return self.avatar


@dataclass
class OrgMember:
    nickname: str = ""
    rank: str = ""
    stars: int = 0
    avatar: str = ""
    href: str = ""

    @property
    def url(self) -> str:
        if self.href:
            return f"{RSI_BASE}{self.href}"
        return ""


@dataclass
class OrgSearchResult:
    orgs: list[Org] = field(default_factory=list)
    total: int = 0
    page: int = 1
    pagesize: int = 12


class OrgsClient:
    """Client for the RSI Organizations REST API. No auth required."""

    def __init__(self):
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def _post(self, endpoint: str, payload: dict) -> dict:
        session = await self._get_session()
        async with session.post(
            f"{RSI_BASE}{endpoint}",
            json=payload,
            headers={"content-type": "application/json", "accept": "application/json"}
        ) as resp:
            return await resp.json(content_type=None)

    # --- Search (JSON) ---

    async def search(self, query: str = "", *, page: int = 1, pagesize: int = 12) -> OrgSearchResult:
        """Search orgs by name. Returns lightweight JSON results (name, symbol, model, icon)."""
        data = await self._post("/api/orgs/searchOrgs", {
            "search": query, "page": page, "pagesize": pagesize
        })
        raw = data.get("data", {})
        orgs = [Org(
            name=r.get("name", ""),
            symbol=r.get("symbol", ""),
            model=r.get("model", ""),
            icon=r.get("icon", ""),
        ) for r in raw.get("resultset", [])]
        return OrgSearchResult(orgs=orgs, total=raw.get("totalrows", 0), page=page, pagesize=pagesize)

    # --- List (HTML parsed) ---

    async def fetch_orgs(self, *, search: str = "", page: int = 1, pagesize: int = 12,
                         sort: str = "size_desc",
                         commitment: list[str] | None = None,
                         language: list[str] | None = None,
                         roleplay: list[str] | None = None,
                         size: list[str] | None = None,
                         model: list[str] | None = None,
                         activity: list[str] | None = None,
                         recruiting: list[str] | None = None) -> OrgSearchResult:
        """Fetch orgs with full details (parsed from HTML). Supports all filter options."""
        payload = {"sort": sort, "search": search, "page": page, "pagesize": pagesize}
        if commitment:
            payload["commitment"] = commitment
        if language:
            payload["language"] = language
        if roleplay:
            payload["roleplay"] = roleplay
        if size:
            payload["size"] = size
        if model:
            payload["model"] = model
        if activity:
            payload["activity"] = activity
        if recruiting:
            payload["recruiting"] = recruiting

        data = await self._post("/api/orgs/getOrgs", payload)
        raw = data.get("data", {})
        html = raw.get("html", "")
        orgs = self._parse_org_html(html)
        return OrgSearchResult(orgs=orgs, total=raw.get("totalrows", 0), page=page, pagesize=pagesize)

    # --- Members ---

    async def fetch_members(self, symbol: str, *, page: int = 1, pagesize: int = 32) -> list[OrgMember]:
        """Fetch members of an org by symbol (e.g. 'TEST')."""
        data = await self._post("/api/orgs/getOrgMembers", {
            "symbol": symbol, "page": page, "pagesize": pagesize
        })
        html = data.get("data", {}).get("html", "")
        return self._parse_member_html(html)

    # --- HTML Parsing ---

    @staticmethod
    def _parse_org_html(html: str) -> list[Org]:
        orgs = []
        blocks = re.split(r'<div class="org-cell', html)
        for block in blocks[1:]:
            org = Org()
            href = re.search(r'href="/orgs/(\w+)"', block)
            if href:
                org.symbol = href.group(1)
                org.href = f"/orgs/{org.symbol}"

            name_match = re.search(r'class="[^"]*name[^"]*">(.*?)</h3>', block)
            if name_match:
                org.name = name_match.group(1).strip()

            avatar_match = re.search(r'<img src="([^"]+)"', block)
            if avatar_match:
                org.avatar = avatar_match.group(1)

            labels = re.findall(
                r'<span class="label">(.*?)</span>\s*<span class="value[^"]*">(.*?)</span>',
                block, re.DOTALL
            )
            for label, value in labels:
                label = label.strip().rstrip(": ")
                value = value.strip()
                if "Archetype" in label:
                    org.archetype = value
                elif "Lang" in label:
                    org.language = value
                elif "Commitment" in label:
                    org.commitment = value
                elif "Recruiting" in label:
                    org.recruiting = value.lower() == "yes"
                elif "Role play" in label:
                    org.roleplay = value.lower() == "yes"
                elif "Members" in label:
                    try:
                        org.member_count = int(value)
                    except ValueError:
                        pass

            if org.symbol:
                orgs.append(org)
        return orgs

    @staticmethod
    def _parse_member_html(html: str) -> list[OrgMember]:
        members = []
        blocks = re.split(r'<li class="member-item', html)
        for block in blocks[1:]:
            member = OrgMember()
            nick = re.search(r'class="[^"]*nick[^"]*">(.*?)<', block)
            if nick:
                member.nickname = nick.group(1).strip()

            rank = re.search(r'class="[^"]*rank[^"]*">(.*?)<', block)
            if rank:
                member.rank = rank.group(1).strip()

            stars_match = re.findall(r'class="[^"]*star[^"]*active', block)
            member.stars = len(stars_match)

            avatar_match = re.search(r'<img src="([^"]+)"', block)
            if avatar_match:
                member.avatar = avatar_match.group(1)

            href_match = re.search(r'href="(/citizens/[^"]+)"', block)
            if href_match:
                member.href = href_match.group(1)

            if member.nickname:
                members.append(member)
        return members
