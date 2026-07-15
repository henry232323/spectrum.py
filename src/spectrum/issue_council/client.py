from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import aiohttp

IC_GRAPHQL_ENDPOINT = "https://api-issue-council.robertsspaceindustries.com/gql"
IC_IDP_ENDPOINT = "https://api-issue-council.robertsspaceindustries.com/idp"
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


@dataclass
class IssueDetails:
    severity: str = ""
    title: str = ""
    category: Optional[dict] = None
    environment: Optional[dict] = None


@dataclass
class IssueCommunity:
    contributionCount: int = 0
    reproductionCount: int = 0
    voteCount: int = 0
    severity: str = ""


@dataclass
class Issue:
    id: str = ""
    code: str = ""
    status: str = ""
    details: Optional[IssueDetails] = None
    community: Optional[IssueCommunity] = None
    openDetails: Optional[dict] = None
    confirmedDetails: Optional[dict] = None
    archivedDetails: Optional[dict] = None
    fixedDetails: Optional[dict] = None
    externalIssue: Optional[dict] = None
    viewerProperties: Optional[dict] = None

    def __post_init__(self):
        if isinstance(self.details, dict):
            self.details = IssueDetails(**self.details)
        if isinstance(self.community, dict):
            self.community = IssueCommunity(**self.community)


@dataclass
class Project:
    id: str = ""
    code: str = ""
    name: str = ""


class IssueCouncilClient:
    """Client for the RSI Issue Council GraphQL API.

    Requires a Bearer token from the IC's OIDC identity provider.
    The IC uses OAuth2 PKCE with client_id='resolve_webui'.

    To get a token: log in at https://issue-council.robertsspaceindustries.com
    and extract the Bearer token from browser devtools (Network tab, Authorization header).
    """

    def __init__(self, access_token: str):
        self._access_token = access_token
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
            IC_GRAPHQL_ENDPOINT,
            json=payload,
            headers={
                "content-type": "application/json",
                "authorization": f"Bearer {self._access_token}",
            }
        ) as resp:
            result = await resp.json(content_type=None)
            if "errors" in result:
                raise RuntimeError(f"Issue Council API error: {result['errors']}")
            return result.get("data", {})

    async def fetch_projects(self) -> list[Project]:
        """Fetch all IC projects (Star Citizen, etc.)."""
        query = _load_query("queries", "Projects")
        data = await self._execute(query, {}, "Projects")
        return [Project(**p) for p in data.get("projects", [])]

    async def fetch_project(self, code: str) -> dict:
        """Fetch a project by code (e.g. 'STAR-CITIZEN')."""
        query = _load_query("queries", "Project") + _load_fragments(
            "ProjectFragment", "ProjectFeatureFragment", "ProjectOptionFragment",
            "SecurityVisibilityFragment", "ProjectOperationalRequirementFragment"
        )
        data = await self._execute(query, {"code": code, "includeOperationalRequirements": True}, "Project")
        return data.get("projectByCode", {})

    async def search_issues(self, project_code: str = "STAR-CITIZEN", *,
                            search: str | None = None, first: int = 10,
                            sort_field: str = "VOTES", sort_order: str = "DESC",
                            status: list[str] | None = None) -> dict:
        """Search issues on the Issue Council.

        Args:
            project_code: Project code (default 'STAR-CITIZEN')
            search: Free text search query
            first: Number of results
            sort_field: VOTES, CREATED_AT, UPDATED_AT
            sort_order: ASC or DESC
            status: Filter by status (OPEN, CONFIRMED, FIXED, ARCHIVED, etc.)
        """
        query = _load_query("queries", "Issues") + _load_fragments(
            "SecurityVisibilityFragment", "IssueSummaryPromotionDetailsFragment",
            "IssuePromotionDetailsFragment"
        )
        variables = {
            "query": {
                "projectCode": project_code,
                "first": first,
                "sort": {"field": sort_field, "order": sort_order},
            }
        }
        if search:
            variables["query"]["search"] = search
        if status:
            variables["query"]["statuses"] = status
        data = await self._execute(query, variables, "Issues")
        raw = data.get("similarIssues", {})
        issues = [Issue(**edge.get("node", {})) for edge in raw.get("edges", [])]
        return {"issues": issues, "totalCount": raw.get("totalCount", 0)}

    async def fetch_notifications(self, first: int = 20) -> dict:
        """Fetch user notifications."""
        query = _load_query("queries", "Notifications")
        data = await self._execute(query, {"first": first}, "Notifications")
        return data.get("notifications", {})

    async def fetch_unread_count(self) -> int:
        """Get unread notification count."""
        query = _load_query("queries", "UnreadNotificationCount")
        data = await self._execute(query, {}, "UnreadNotificationCount")
        return data.get("unreadNotificationCount", 0)

    async def mark_notifications_read(self, notification_ids: list[str]) -> dict:
        """Mark notifications as read."""
        query = _load_query("mutations", "ChangeNotificationsReadStatus")
        data = await self._execute(query, {"ids": notification_ids, "isRead": True}, "ChangeNotificationsReadStatus")
        return data
