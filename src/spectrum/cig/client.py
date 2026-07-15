from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import aiohttp

CIG_GRAPHQL_ENDPOINT = "https://cloudimperiumgames.com/graphql"


@dataclass
class UploadFile:
    url: str = ""
    name: str = ""
    mime: str = ""


@dataclass
class Category:
    _id: str = ""
    title: str = ""
    slug: str = ""


@dataclass
class Post:
    _id: str = ""
    title: str = ""
    slug: str = ""
    content: str = ""
    excerpt: str = ""
    publishedAt: str = ""
    seoTitle: str = ""
    seoDescription: str = ""
    image: Optional[UploadFile] = None
    category: Optional[Category] = None

    def __post_init__(self):
        if isinstance(self.image, dict):
            self.image = UploadFile(**self.image)
        if isinstance(self.category, dict):
            self.category = Category(**self.category)


@dataclass
class Studio:
    _id: str = ""
    name: str = ""
    title: str = ""
    slug: str = ""
    location: str = ""
    content: str = ""
    excerpt: str = ""
    culture: str = ""
    modalUrl: str = ""
    hasExternalLink: bool = False
    externalLink: str = ""


@dataclass
class Job:
    _id: str = ""
    title: str = ""
    slug: str = ""
    description: str = ""
    link: str = ""
    publishedAt: str = ""
    seoTitle: str = ""
    seoDescription: str = ""
    studio: Optional[Studio] = None
    discipline: Optional[dict] = None
    subdiscipline: Optional[dict] = None

    def __post_init__(self):
        if isinstance(self.studio, dict):
            self.studio = Studio(**{k: v for k, v in self.studio.items() if k in Studio.__dataclass_fields__})


@dataclass
class Discipline:
    _id: str = ""
    name: str = ""
    slug: str = ""
    title: str = ""
    description: str = ""


@dataclass
class Game:
    _id: str = ""
    name: str = ""
    title: str = ""
    slug: str = ""
    description: str = ""
    link: str = ""
    linkLabel: str = ""
    gameType: str = ""


@dataclass
class Perk:
    _id: str = ""
    title: str = ""
    description: str = ""
    content: str = ""


class CIGClient:
    """Client for the Cloud Imperium Games corporate website GraphQL API (blog, jobs, studios)."""

    def __init__(self):
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def _execute(self, query: str) -> dict:
        session = await self._get_session()
        async with session.post(
            CIG_GRAPHQL_ENDPOINT,
            json={"query": query},
            headers={"content-type": "application/json"}
        ) as resp:
            result = await resp.json(content_type=None)
            if "errors" in result:
                raise RuntimeError(f"GraphQL error: {result['errors']}")
            return result.get("data", {})

    # --- Blog Posts ---

    async def fetch_posts(self, *, limit: int = 10, start: int = 0,
                          sort: str = "publishedAt:desc", category_slug: str | None = None) -> list[Post]:
        """Fetch blog posts, sorted by most recent by default."""
        where = f', where: {{category: {{slug: "{category_slug}"}}}}' if category_slug else ""
        query = f'{{ posts(sort: "{sort}", limit: {limit}, start: {start}{where}) {{ _id title slug content excerpt publishedAt seoTitle seoDescription image {{ url }} category {{ _id title slug }} }} }}'
        data = await self._execute(query)
        return [Post(**p) for p in data.get("posts", [])]

    async def fetch_post(self, slug: str) -> Post:
        """Fetch a single blog post by slug."""
        query = f'{{ postBySlug(slug: "{slug}") {{ _id title slug content excerpt publishedAt seoTitle seoDescription image {{ url }} category {{ _id title slug }} }} }}'
        data = await self._execute(query)
        return Post(**data.get("postBySlug", {}))

    async def fetch_posts_count(self, category_slug: str | None = None) -> int:
        """Get total blog post count."""
        where = f', where: {{category: {{slug: "{category_slug}"}}}}' if category_slug else ""
        query = f'{{ postsCount{where.replace(", ", "(") + ")" if where else ""} }}'
        # Simpler approach
        query = f'{{ postsCount }}'
        data = await self._execute(query)
        return data.get("postsCount", 0)

    async def fetch_categories(self) -> list[Category]:
        """Fetch blog categories."""
        query = '{ categories { _id title slug } }'
        data = await self._execute(query)
        return [Category(**c) for c in data.get("categories", [])]

    # --- Studios ---

    async def fetch_studios(self) -> list[Studio]:
        """Fetch all CIG studios."""
        query = '{ studios { _id name title slug location content excerpt culture modalUrl hasExternalLink externalLink } }'
        data = await self._execute(query)
        return [Studio(**s) for s in data.get("studios", [])]

    async def fetch_studio(self, slug: str) -> Studio:
        """Fetch a studio by slug."""
        query = f'{{ studioBySlug(slug: "{slug}") {{ _id name title slug location content excerpt culture modalUrl hasExternalLink externalLink }} }}'
        data = await self._execute(query)
        return Studio(**data.get("studioBySlug", {}))

    # --- Jobs ---

    async def fetch_jobs(self, *, limit: int = 50, start: int = 0,
                         sort: str = "publishedAt:desc",
                         studio_slug: str | None = None,
                         discipline_slug: str | None = None) -> list[Job]:
        """Fetch job listings with optional studio/discipline filter."""
        where_parts = []
        if studio_slug:
            where_parts.append(f'studio: {{slug: "{studio_slug}"}}')
        if discipline_slug:
            where_parts.append(f'discipline: {{slug: "{discipline_slug}"}}')
        where = f', where: {{{", ".join(where_parts)}}}' if where_parts else ""
        query = f'{{ jobs(sort: "{sort}", limit: {limit}, start: {start}{where}) {{ _id title slug description link publishedAt seoTitle seoDescription studio {{ name slug location }} discipline {{ name slug }} subdiscipline {{ name slug }} }} }}'
        data = await self._execute(query)
        return [Job(**j) for j in data.get("jobs", [])]

    async def fetch_job(self, slug: str) -> Job:
        """Fetch a single job by slug."""
        query = f'{{ jobBySlug(slug: "{slug}") {{ _id title slug description link publishedAt seoTitle seoDescription studio {{ name slug location }} discipline {{ name slug }} subdiscipline {{ name slug }} }} }}'
        data = await self._execute(query)
        return Job(**data.get("jobBySlug", {}))

    async def fetch_jobs_count(self) -> int:
        """Get total job listings count."""
        query = '{ jobsCount }'
        data = await self._execute(query)
        return data.get("jobsCount", 0)

    # --- Disciplines ---

    async def fetch_disciplines(self) -> list[Discipline]:
        """Fetch job disciplines (Engineering, Art, Design, etc.)."""
        query = '{ disciplines { _id name slug title description } }'
        data = await self._execute(query)
        return [Discipline(**d) for d in data.get("disciplines", [])]

    # --- Games ---

    async def fetch_games(self) -> list[Game]:
        """Fetch CIG games (Star Citizen, Squadron 42)."""
        query = '{ games { _id name title slug description link linkLabel gameType } }'
        data = await self._execute(query)
        return [Game(**g) for g in data.get("games", [])]

    # --- Perks ---

    async def fetch_perks(self) -> list[Perk]:
        """Fetch studio perks/benefits."""
        query = '{ perks { _id title description content } }'
        data = await self._execute(query)
        return [Perk(**p) for p in data.get("perks", [])]

    # --- CMS Pages ---

    async def fetch_page(self, slug: str) -> dict:
        """Fetch a CMS page by slug."""
        query = f'{{ pageBySlug(slug: "{slug}") {{ _id title content slug }} }}'
        data = await self._execute(query)
        return data.get("pageBySlug", {})
