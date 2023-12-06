from typing import Optional

from . import member, abc
from .emoji import Emoji
from .role import Role
from .. import httpclient
from ..util import find


class Community(abc.Identifier):
    """
{
  "0": {
    "id": "1",
    "type": "public",
    "slug": "SC",
    "name": "Star Citizen",
    "avatar": "https://robertsspaceindustries.com/media/swz5gohfczhjqr/heap_infobox/SC_Gold.jpg?v=1503107521",
    "banner": "https://robertsspaceindustries.com/media/yos4xd23ikf96r/source/After_GC2017_SPECTRUMBANNER.jpg?v=1504636757",
    "lobbies": [
        Lobby
    ],
    "forum_channel_groups": {
      "0": {
        "id": "1",
        "community_id": "1",
        "order": 0,
        "name": "Official",
        "channels": [
          {
            "id": "1",
            "community_id": "1",
            "group_id": "1",
            "order": 0,
            "name": "Announcements",
            "description": "Official Star Citizen announcements.",
            "color": "e05248",
            "sort_filter": "time-created",
            "label_required": false,
            "threads_count": 308,
            "labels": [
              {
                "id": "1",
                "channel_id": "1",
                "name": "Community",
                "subscription_key": "community:1:forum_label:1:ef02e5e178d66ec40e15e4e114974a91d31682dc",
                "notification_subscription": null
              },
              {
                "id": "3",
                "channel_id": "1",
                "name": "Live Service",
                "subscription_key": "community:1:forum_label:3:bd6ea6c5a7923607219bdb079b30babc985cfc98",
                "notification_subscription": null
              },
              {
                "id": "2",
                "channel_id": "1",
                "name": "Patch",
                "subscription_key": "community:1:forum_label:2:45189c79a69c364c17db0dcc8228f4286835edc3",
                "notification_subscription": null
              },
              {
                "id": "5",
                "channel_id": "1",
                "name": "Spectrum",
                "subscription_key": "community:1:forum_label:5:1e0a0aacd1c6129e8ecff627fa6e1bef3d75e958",
                "notification_subscription": null
              },
              {
                "id": "4",
                "channel_id": "1",
                "name": "Store Update",
                "subscription_key": "community:1:forum_label:4:71f9e271f721ea69f49786ddd8d5f838fb193a29",
                "notification_subscription": null
              }
            ],
            "subscription_key": "community:1:forum_channel:1:cb0800f05bdb0f3976e20adbd2c12a145b4a83ce",
            "permissions": {
              "4": {
                "create_thread": 0,
                "manage": 0
              },
              "5": {
                "create_thread": 0,
                "manage": 0
              },
              "6": {
                "create_thread": 0,
                "manage": 0
              },
              "11": {
                "create_thread": 0
              },
              "137732": {
                "create_thread": 0,
                "manage": 0
              }
            },
            "notification_subscription": null
          }
        ]
      },
    },
    "roles": [
      Role
    ]
  }
}
    """

    def __init__(self, client: 'httpclient.HTTPClient', payload: dict):
        self._client = client
        self.id = int(payload["id"])
        self.slug = payload['slug']
        self.name = payload['name']
        self.avatar_url = payload['avatar']
        self.banner_url = payload['banner']
        self._roles = {}
        for role in payload['roles']:
            self._replace_role(role)

        self.lobbies = tuple(client._replace_lobby(lobby) for lobby in payload['lobbies'])
        self.forums = tuple(client._replace_forum(forum) for forum in (
            payload['forum_channel_groups'].values() if isinstance(payload['forum_channel_groups'], dict) else payload[
                'forum_channel_groups']))

    def __repr__(self):
        return f"Community(id={repr(self.id)}, name={repr(self.name)}, slug={repr(self.slug)})"

    @property
    def roles(self) -> list[Role]:
        return list(self._roles.values())

    def get_lobby(self, lobby_id: str | int):
        return self._client.get_lobby(lobby_id)

    async def fetch_members(self, page=1, pagesize=12, sort='displayname', sort_descending=0):
        members = await self._client._http.fetch_community_members(
            {"community_id": self.id, 'page': page, 'pagesize': pagesize, 'sort_descending': sort_descending,
             'sort': sort})
        return [self._client._replace_member(r) for r in members]

    async def fetch_roles(self, member: member.Member):
        roles = await self._client._http.fetch_member_roles({"member_id": member.id, "community_id": self.id})
        return [find(self._roles.values(), r) for r in roles]

    async def fetch_counters(self, member: member.Member):
        resp = await self._client._http.fetch_member_counters({"member_id": member.id, "community_id": self.id})
        return resp

    async def fetch_emojis(self, member: member.Member):
        emojis = await self._client._http.fetch_emojis({"community_id": self.id})
        return [Emoji(r) for r in emojis]

    async def fetch_online_count(self, member: member.Member):
        resp = await self._client._http.fetch_emojis({"community_id": self.id})
        return {self._client.get_lobby(lid): count for lid, count in resp.items()}

    async def create_category_group(self, name: str):
        resp = await self._client._http.create_categories_group(
            {"community_id": self.id, "name": name}
        )

        forum = self._client._replace_forum(resp)
        self.forums = (*self.forums, forum)

        return forum

    async def create_lobby(self, name: str, *, color, description, type='public'):
        resp = await self._client._http.create_categories_group(
            {"community_id": self.id, "name": name, description: description, color: color, type: type}
        )

        forum = self._client._replace_forum(resp)
        self.forums = (*self.forums, forum)

        return forum

    def get_role(self, role_id: str) -> Optional[Role]:
        return self._roles.get(int(role_id))

    def _replace_role(self, payload: dict):
        role = self.get_role(payload['id'])
        if role:
            role.__init__(self._client, payload)
        else:
            self._roles[int(payload['id'])] = role = Role(self._client, payload)

        return role
