from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from . import message, abc
from .. import httpclient
from ..util.datetime import parse_timestamp
from ..util.entity_ranges import get_entity_ranges

if TYPE_CHECKING:
    from .member import Member


class Lobby(abc.Identifier, abc.Subscription):
    """
    {
        "id": "22066",
        "type": "public",
        "community_id": "1",
        "name": "becoming-a-citizen",
        "description": "Interested in joining Star Citizen? Introduce yourself and ask the community questions!",
        "color": "63A3E6",
        "icon": null,
        "time_created": 1487781367,
        "subscription_key": "community:1:message_lobby:22066:83a034f6f8758ecb049eccb29c4ddf38c18bd924",
        "leader_id": null,
        "online_members_count": 12,
        "permissions": {
            "4": {
                "read": 1,
                "send_message": 1,
                "manage": 0
            },
            "5": {
                "read": 1,
                "manage": 0
            },
            "6": {
                "read": 1
            },
            "137732": {
                "manage": 0
            }
        },
        "last_read": null,
        "latest": null,
        "members": null,
        "new_messages": null,
        "last_message": null,
        "active_guide_session": null,
        "blocked_recipients": null
    }
    """

    def __init__(self, client: 'httpclient.HTTPClient', payload: dict):
        self._client = client
        self.id = int(payload["id"])
        self.type = payload.get('type')
        self.community_id = int(payload['community_id']) if payload.get('community_id') else None
        self.name = payload.get('name')
        self.description = payload.get('description')
        self.color = payload.get('color')
        self.icon = payload.get('icon')
        self.time_created = parse_timestamp(payload['time_created']) if payload.get('time_created') else None
        self.subscription_key = payload.get('subscription_key')
        self.leader_id = int(payload['leader_id']) if payload.get('leader_id') else None
        self.online_members_count = payload.get('online_members_count')
        self.permissions = payload.get('permissions')
        if payload.get('members') is None:
            self._members = None
        else:
            self._members = {member['id']: client._replace_member(member) for member in payload['members']}

    @property
    def members(self):
        if self._members is None:
            return None
        return list(self._members.values())

    @property
    def community(self):
        return self._client.get_community(self.community_id)

    @property
    def leader(self):
        return self._client.get_member(self.leader_id)

    def __repr__(self):
        return f"Lobby(id={repr(self.id)}, name={repr(self.name)})"

    async def send(self, content: str, *, add_links: bool = True, highlight_role_id: str | None = None,
                   media_id: str | None = None, embed_url: str | None = None) -> message.Message:
        """Send a message to this lobby. URLs in content are auto-linked unless add_links=False. Attach a preview card via embed_url or media_id."""
        entity_ranges = []
        entity_map = {}

        if add_links:
            raw_ranges = get_entity_ranges(content)
            for er in raw_ranges:
                entity_ranges.append({"offset": er.offset, "length": er.length, "key": er.key})
                entity_map[str(er.key)] = {"type": "LINK", "mutability": "IMMUTABLE", "data": {"href": content[er.offset:er.offset + er.length]}}

        if embed_url and not media_id:
            embed = await self._client._http.fetch_embed(embed_url)
            media_id = embed['id']

        payload = await self._client._http.send_message({
            "lobby_id": self.id,
            "content_state": {"blocks": [
                {"key": "bpeol", "text": content, "type": "unstyled", "depth": 0,
                 "inlineStyleRanges": [], "entityRanges": entity_ranges, "data": {}}], "entityMap": entity_map},
            "plaintext": content, "media_id": media_id, "highlight_role_id": highlight_role_id
        })

        return message.Message(self._client, payload)

    async def set_motd(self, motd: str) -> None:
        """Set the lobby's message of the day."""
        await self._client._http.set_motd({"lobby_id": str(self.id), "motd": motd})

    async def fetch_presence(self) -> list[Member]:
        """Fetch members currently present in this lobby."""
        presences = await self._client._http.fetch_presences(dict(lobby_id=self.id))
        return [self._client._replace_member(p) for p in presences]

    async def fetch_history(self, count: int = 50) -> AsyncIterator[message.Message]:
        """Async iterator yielding up to `count` messages in reverse chronological order."""
        first_message = None
        while count > 0:
            resp = await self._client._http.fetch_history(
                {"lobby_id": self.id, "timeframe": "before", "message_id": first_message, "size": count}
            )
            messages = resp['messages']
            if messages:
                first_message = messages[0]['id']
                count -= len(messages)
                for msg in messages:
                    yield self._client._replace_message(msg)

            if len(messages) < 50:
                break
