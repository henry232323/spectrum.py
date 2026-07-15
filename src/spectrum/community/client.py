from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from aiographql.client import GraphQLClient, GraphQLRequest

from .models import (
    Account, AccountCard, AccountStats, Comment, Event, Post, PostCard,
    Tag, Ship, Manufacturer, Media, PaginatedResult, Settings, ConnectedAccountData, Badge
)

if TYPE_CHECKING:
    from ..httpclient import HTTPClient

COMMUNITY_HUB_GRAPHQL_ENDPOINT = "https://robertsspaceindustries.com/community-hub/api/v1/graphql"
GRAPHQL_DIR = Path(__file__).parent / "graphql"


def _load_query(category: str, name: str) -> str:
    path = GRAPHQL_DIR / category / f"{name}.graphql"
    return path.read_text()


def _load_fragments(*names: str) -> str:
    parts = []
    for name in names:
        path = GRAPHQL_DIR / "fragments" / f"{name}.graphql"
        if path.exists():
            parts.append(path.read_text())
    return "\n".join(parts)


class CommunityHubClient:
    def __init__(self, rsi_token: str | None = None, device_id: str | None = None):
        headers = {}
        if rsi_token:
            headers["x-rsi-token"] = rsi_token
            headers["cookie"] = f"Rsi-Token={rsi_token}"
            if device_id:
                headers["cookie"] += f"; _rsi_device={device_id}"

        self._client = GraphQLClient(
            endpoint=COMMUNITY_HUB_GRAPHQL_ENDPOINT,
            headers=headers,
        )

    @classmethod
    def from_client(cls, client: HTTPClient) -> CommunityHubClient:
        """Create a CommunityHubClient using auth from an existing HTTPClient/Client."""
        return cls(
            rsi_token=client._http._rsi_token,
            device_id=client._http._device_id,
        )

    async def _execute(self, query: str, variables: dict | None = None, operation: str | None = None) -> dict:
        request = GraphQLRequest(
            query=query,
            variables=variables or {},
            operation=operation,
            validate=False,
        )
        resp = await self._client.query(request=request)
        return resp.data

    # --- Account ---

    async def fetch_user_profile(self, nickname: str) -> Account:
        """Fetch a Community Hub user profile by nickname."""
        query = _load_query("queries", "getAccount") + _load_fragments("Account", "AccountStats")
        data = await self._execute(query, {"CreatorQuery": {"nickname": nickname}}, "getAccount")
        return Account(**data.get("creator", {}))

    async def fetch_user_stats(self, nickname: str) -> AccountStats:
        """Fetch account stats (followers, views, upvotes) for a user."""
        query = _load_query("queries", "getAccountStats") + _load_fragments("AccountStats")
        data = await self._execute(query, {"CreatorQuery": {"nickname": nickname}}, "getAccountStats")
        return AccountStats(**data.get("creatorStats", {}))

    async def fetch_authenticated_user(self) -> ConnectedAccountData:
        """Fetch the currently authenticated user's profile."""
        query = _load_query("queries", "getAuthenticatedUser") + _load_fragments("Account", "AccountStats", "ConnectedAccount", "ConnectedAccountData", "Settings", "Tag")
        data = await self._execute(query, {}, "getAuthenticatedUser")
        raw = data.get("authenticatedUser", {})
        user_data = raw.get("user", raw)
        return ConnectedAccountData(**user_data)

    async def fetch_followers(self, nickname: str, page: int = 1, page_size: int = 12) -> PaginatedResult:
        """Fetch followers of a user."""
        query = _load_query("queries", "getFollowers") + _load_fragments("AccountCard", "AccountStats")
        data = await self._execute(query, {"FollowersQuery": {"nickname": nickname, "page": page, "pageSize": page_size}}, "getFollowers")
        raw = data.get("followers", {})
        result = PaginatedResult(totalCount=raw.get("totalCount", 0), hasNextPage=raw.get("hasNextPage", False))
        result.metaData = [AccountCard(**a) for a in raw.get("metaData", [])]
        return result

    async def fetch_following(self, nickname: str, page: int = 1, page_size: int = 12) -> PaginatedResult:
        """Fetch accounts a user is following."""
        query = _load_query("queries", "getFollowing") + _load_fragments("AccountCard", "AccountStats")
        data = await self._execute(query, {"FollowingQuery": {"nickname": nickname, "page": page, "pageSize": page_size}}, "getFollowing")
        raw = data.get("following", {})
        result = PaginatedResult(totalCount=raw.get("totalCount", 0), hasNextPage=raw.get("hasNextPage", False))
        result.metaData = [AccountCard(**a) for a in raw.get("metaData", [])]
        return result

    async def follow_account(self, nickname: str) -> Account:
        """Follow a user."""
        query = _load_query("mutations", "followAccount") + _load_fragments("Account", "AccountStats")
        data = await self._execute(query, {"nickname": nickname}, "followAccount")
        return Account(**data.get("followAccount", {}))

    async def unfollow_account(self, nickname: str) -> Account:
        """Unfollow a user."""
        query = _load_query("mutations", "unfollowAccount") + _load_fragments("Account", "AccountStats")
        data = await self._execute(query, {"nickname": nickname}, "unfollowAccount")
        return Account(**data.get("unfollowAccount", {}))

    # --- Posts ---

    async def fetch_posts(self, query_params: dict) -> PaginatedResult:
        """Fetch posts with query parameters."""
        query = _load_query("queries", "getPosts") + _load_fragments(
            "AudioCard", "ImageCard", "LiveCard", "TextCard", "VideoCard",
            "AccountCard", "AccountStats", "AudioCardCarousel", "ImageCardCarousel",
            "LiveCardCarousel", "TextCardCarousel", "VideoCardCarousel"
        )
        data = await self._execute(query, {"PostsQuery": query_params}, "getPosts")
        raw = data.get("posts", {})
        result = PaginatedResult(totalCount=raw.get("totalCount", 0), hasNextPage=raw.get("hasNextPage", False))
        result.metaData = [PostCard(**p) for p in raw.get("metaData", [])]
        return result

    async def fetch_post(self, slug: str) -> Post:
        """Fetch a single post by slug."""
        query = _load_query("queries", "getPost") + _load_fragments(
            "Audio", "Image", "Live", "Text", "Video",
            "Account", "AccountStats", "LeanAccount", "Media", "Tag", "Ship", "Event", "Manufacturer"
        )
        data = await self._execute(query, {"PostQuery": {"slug": slug}}, "getPost")
        return Post(**data.get("post", {}))

    async def fetch_homepage_posts(self, query_params: dict) -> PaginatedResult:
        """Fetch homepage/featured posts."""
        query = _load_query("queries", "getHomepagePosts") + _load_fragments(
            "AudioCard", "ImageCard", "LiveCard", "TextCard", "VideoCard",
            "AccountCard", "AccountStats", "AudioCardCarousel", "ImageCardCarousel",
            "LiveCardCarousel", "TextCardCarousel", "VideoCardCarousel"
        )
        data = await self._execute(query, {"PostsQuery": query_params}, "getHomepagePosts")
        raw = data.get("homepagePosts", {})
        result = PaginatedResult(totalCount=raw.get("totalCount", 0), hasNextPage=raw.get("hasNextPage", False))
        result.metaData = [PostCard(**p) for p in raw.get("metaData", [])]
        return result

    async def create_post(self, post_params: dict) -> Post:
        """Create a new post."""
        query = _load_query("mutations", "createPost") + _load_fragments(
            "Audio", "Image", "Live", "Text", "Video",
            "Account", "AccountStats", "LeanAccount", "Media", "Tag", "Ship", "Event", "Manufacturer"
        )
        data = await self._execute(query, {"postParameters": post_params}, "createPost")
        return Post(**data.get("createPost", {}))

    async def edit_post(self, post_params: dict) -> Post:
        """Edit an existing post."""
        query = _load_query("mutations", "editPost") + _load_fragments(
            "Audio", "Image", "Live", "Text", "Video",
            "Account", "AccountStats", "LeanAccount", "Media", "Tag", "Ship", "Event", "Manufacturer"
        )
        data = await self._execute(query, {"postParameters": post_params}, "editPost")
        return Post(**data.get("editPost", {}))

    async def delete_post(self, uid: str) -> None:
        """Delete a post by UID."""
        query = _load_query("mutations", "deletePost")
        await self._execute(query, {"uid": uid}, "deletePost")

    async def upvote_post(self, uid: str) -> None:
        """Upvote a post."""
        query = _load_query("mutations", "upvotePost")
        await self._execute(query, {"uid": uid}, "upvotePost")

    async def downvote_post(self, uid: str) -> None:
        """Remove upvote from a post."""
        query = _load_query("mutations", "downvotePost")
        await self._execute(query, {"uid": uid}, "downvotePost")

    # --- Comments ---

    async def fetch_comments(self, query_params: dict) -> PaginatedResult:
        """Fetch comments for a post."""
        query = _load_query("queries", "getComments") + _load_fragments("Comment", "Account", "AccountStats")
        data = await self._execute(query, {"CommentsQuery": query_params}, "getComments")
        raw = data.get("comments", {})
        result = PaginatedResult(totalCount=raw.get("totalCount", 0), hasNextPage=raw.get("hasNextPage", False))
        result.metaData = [Comment(**c) for c in raw.get("metaData", [])]
        return result

    async def fetch_comment_replies(self, query_params: dict) -> PaginatedResult:
        """Fetch replies to a comment."""
        query = _load_query("queries", "getCommentsReplies") + _load_fragments("Comment", "Account", "AccountStats")
        data = await self._execute(query, {"CommentsQuery": query_params}, "getCommentsReplies")
        raw = data.get("commentsReplies", {})
        result = PaginatedResult(totalCount=raw.get("totalCount", 0), hasNextPage=raw.get("hasNextPage", False))
        result.metaData = [Comment(**c) for c in raw.get("metaData", [])]
        return result

    async def create_comment(self, comment_params: dict) -> Comment:
        """Create a comment on a post."""
        query = _load_query("mutations", "createComment") + _load_fragments("Comment", "Account", "AccountStats")
        data = await self._execute(query, {"commentParameters": comment_params}, "createComment")
        return Comment(**data.get("createComment", {}))

    # --- Events ---

    async def fetch_events(self, query_params: dict) -> PaginatedResult:
        """Fetch community events."""
        query = _load_query("queries", "getEvents") + _load_fragments("Event", "Media")
        data = await self._execute(query, {"EventQuery": query_params}, "getEvents")
        raw = data.get("events", {})
        result = PaginatedResult(totalCount=raw.get("totalCount", 0), hasNextPage=raw.get("hasNextPage", False))
        result.metaData = [Event(**e) for e in raw.get("metaData", [])]
        return result

    async def fetch_events_info(self, query_params: dict) -> PaginatedResult:
        """Fetch events metadata/info."""
        query = _load_query("queries", "getEventsInfo") + _load_fragments("Event", "Media")
        data = await self._execute(query, {"EventQuery": query_params}, "getEventsInfo")
        raw = data.get("eventsInfo", {})
        result = PaginatedResult(totalCount=raw.get("totalCount", 0), hasNextPage=raw.get("hasNextPage", False))
        result.metaData = [Event(**e) for e in raw.get("metaData", [])]
        return result

    # --- Tags & Ships ---

    async def fetch_tags(self) -> list[Tag]:
        """Fetch available tags."""
        query = _load_query("queries", "getTags") + _load_fragments("Tag")
        data = await self._execute(query, {}, "getTags")
        return [Tag(**t) for t in data.get("tags", [])]

    async def fetch_ships(self) -> list[Ship]:
        """Fetch available ships."""
        query = _load_query("queries", "getShips") + _load_fragments("Ship", "Manufacturer")
        data = await self._execute(query, {}, "getShips")
        return [Ship(**s) for s in data.get("ships", [])]

    async def fetch_manufacturers(self) -> list[Manufacturer]:
        """Fetch ship manufacturers."""
        query = _load_query("queries", "getManufacturers") + _load_fragments("Manufacturer")
        data = await self._execute(query, {}, "getManufacturers")
        return [Manufacturer(**m) for m in data.get("manufacturers", [])]
