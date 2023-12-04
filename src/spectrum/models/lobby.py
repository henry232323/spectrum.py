import asyncio
from datetime import datetime

from . import message, abc
from .. import client


class Lobby(abc.Identifier):
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

    def __init__(self, client: 'client.Client', payload: dict):
        self._client = client
        self.id = int(payload["id"])
        self.type = payload['type']
        self.community_id = int(payload['community_id']) if payload['community_id'] else None
        self.name = payload['name']
        self.description = payload['description']
        self.color = payload['color']
        self.icon = payload['icon']
        self.time_created = datetime.utcfromtimestamp(payload['time_created'])
        self.subscription_key = payload['subscription_key']
        self.leader_id = int(payload['leader_id']) if payload['leader_id'] else None
        self.online_members_count = payload.get('online_members_count')
        self.permissions = payload.get('permissions')
        self._members = {member['id']: client._replace_member(member) for member in (payload['members'] or [])}

        asyncio.create_task(self.fetch_presence())

    @property
    def members(self):
        return list(self._members.values())

    @property
    def community(self):
        return self._client.get_community(self.community_id)

    @property
    def leader(self):
        return self._client.get_member(self.leader_id)

    def __repr__(self):
        return f"Lobby(id={repr(self.id)}, name={repr(self.name)})"

    async def send(self, content: str):
        payload = await self._client._http.send_message({
            "lobby_id": self.id,
            "content_state": {"blocks": [
                {"key": "bpeol", "text": content, "type": "unstyled", "depth": 0,
                 "inlineStyleRanges": [], "entityRanges": [], "data": {}}], "entityMap": {}},
            "plaintext": content, "media_id": None, "highlight_role_id": None
        })

        return message.Message(self._client, dict(message=payload))

    async def fetch_presence(self):
        presences = await self._client._http.fetch_presences(dict(lobby_id=self.id))
        members = []
        for presence in presences:
            members.append(self._client._replace_member(presence))

        return members
