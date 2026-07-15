from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import aiohttp

GALACTAPEDIA_GRAPHQL_ENDPOINT = "https://robertsspaceindustries.com/galactapedia/graphql"
GRAPHQL_DIR = Path(__file__).parent / "graphql"


def _load_query(name: str) -> str:
    path = GRAPHQL_DIR / "queries" / f"{name}.graphql"
    return path.read_text()


@dataclass
class ArticleThumbnail:
    url: str = ""
    name: str = ""
    type: str = ""


@dataclass
class ArticleCategory:
    id: str = ""
    name: str = ""
    slug: str = ""


@dataclass
class ArticleTag:
    id: str = ""
    name: str = ""
    slug: str = ""


@dataclass
class Article:
    id: str = ""
    title: str = ""
    slug: str = ""
    body: str = ""
    thumbnail: Optional[ArticleThumbnail] = None
    categories: list[ArticleCategory] = field(default_factory=list)
    tags: list[ArticleTag] = field(default_factory=list)
    relatedArticles: list[dict] = field(default_factory=list)

    def __post_init__(self):
        if isinstance(self.thumbnail, dict):
            self.thumbnail = ArticleThumbnail(**self.thumbnail)
        self.categories = [ArticleCategory(**c) if isinstance(c, dict) else c for c in self.categories]
        self.tags = [ArticleTag(**t) if isinstance(t, dict) else t for t in self.tags]


@dataclass
class Category:
    id: str = ""
    name: str = ""
    slug: str = ""
    parent: Optional[dict] = None
    thumbnail: Optional[ArticleThumbnail] = None

    def __post_init__(self):
        if isinstance(self.thumbnail, dict):
            self.thumbnail = ArticleThumbnail(**self.thumbnail)


@dataclass
class Tag:
    id: str = ""
    name: str = ""
    slug: str = ""


@dataclass
class PageInfo:
    hasNextPage: bool = False
    hasPreviousPage: bool = False
    startCursor: str = ""
    endCursor: str = ""


@dataclass
class PaginatedResult:
    items: list = field(default_factory=list)
    totalCount: int = 0
    pageInfo: Optional[PageInfo] = None

    def __post_init__(self):
        if isinstance(self.pageInfo, dict):
            self.pageInfo = PageInfo(**self.pageInfo)


class GalactapediaClient:
    """Client for the RSI Galactapedia GraphQL API (lore wiki)."""

    def __init__(self):
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def _execute(self, query: str, variables: dict | None = None, operation: str | None = None) -> dict:
        session = await self._get_session()
        payload = {"query": query, "variables": variables or {}}
        if operation:
            payload["operationName"] = operation
        async with session.post(
            GALACTAPEDIA_GRAPHQL_ENDPOINT,
            json=payload,
            headers={"content-type": "application/json", "accept": "application/json"}
        ) as resp:
            result = await resp.json(content_type=None)
            if "errors" in result:
                raise RuntimeError(f"GraphQL error: {result['errors']}")
            return result.get("data", {})

    async def fetch_article(self, id: str) -> Article:
        """Fetch a single galactapedia article by ID."""
        query = f'{{ Article(id: "{id}") {{ id title slug body thumbnail {{ url name type }} }} }}'
        data = await self._execute(query)
        return Article(**data.get("Article", {}))

    async def search_articles(self, *, first: int = 10,
                              skip: int = 0, after: str | None = None) -> PaginatedResult:
        """Search/list galactapedia articles with pagination."""
        args = [f'first: {first}']
        if skip:
            args.append(f'skip: {skip}')
        if after:
            args.append(f'after: "{after}"')
        args_str = ", ".join(args)
        query = f'{{ allArticle({args_str}) {{ edges {{ node {{ id title slug body thumbnail {{ url name type }} }} cursor }} pageInfo {{ hasNextPage hasPreviousPage startCursor endCursor }} totalCount }} }}'
        data = await self._execute(query)
        raw = data.get("allArticle", {})
        edges = raw.get("edges", [])
        result = PaginatedResult(
            totalCount=raw.get("totalCount", 0),
            pageInfo=raw.get("pageInfo"),
        )
        result.items = [Article(**edge.get("node", {})) for edge in edges]
        return result

    async def fetch_category(self, id: str) -> Category:
        """Fetch a galactapedia category by ID."""
        query = f'{{ Category(id: "{id}") {{ id name slug thumbnail {{ url name type }} }} }}'
        data = await self._execute(query)
        return Category(**data.get("Category", {}))

    async def search_categories(self, *, first: int = 50, skip: int = 0) -> PaginatedResult:
        """List galactapedia categories."""
        query = f'{{ allCategory(first: {first}, skip: {skip}) {{ edges {{ node {{ id name slug thumbnail {{ url }} }} cursor }} pageInfo {{ hasNextPage }} totalCount }} }}'
        data = await self._execute(query)
        raw = data.get("allCategory", {})
        edges = raw.get("edges", [])
        result = PaginatedResult(
            totalCount=raw.get("totalCount", 0),
            pageInfo=raw.get("pageInfo"),
        )
        result.items = [Category(**edge.get("node", {})) for edge in edges]
        return result

    async def fetch_tag(self, id: str) -> Tag:
        """Fetch a galactapedia tag by ID."""
        query = f'{{ Tag(id: "{id}") {{ id name slug }} }}'
        data = await self._execute(query)
        return Tag(**data.get("Tag", {}))

    async def search_tags(self, *, first: int = 50, skip: int = 0) -> PaginatedResult:
        """List galactapedia tags."""
        query = f'{{ allTag(first: {first}, skip: {skip}) {{ edges {{ node {{ id name slug }} cursor }} pageInfo {{ hasNextPage }} totalCount }} }}'
        data = await self._execute(query)
        raw = data.get("allTag", {})
        edges = raw.get("edges", [])
        result = PaginatedResult(
            totalCount=raw.get("totalCount", 0),
            pageInfo=raw.get("pageInfo"),
        )
        result.items = [Tag(**edge.get("node", {})) for edge in edges]
        return result

    async def fetch_homepage(self) -> dict:
        """Fetch galactapedia homepage data (featured articles)."""
        query = '{ Homepage { id homepageTitle featuredArticle { ... on Article { id title slug } } } }'
        data = await self._execute(query)
        return data.get("Homepage", {})
