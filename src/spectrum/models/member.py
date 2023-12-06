from typing import Optional

from . import abc, lobby, message, community
from .badge import Badge
from .presence import Presence
from .. import httpclient


class Member(abc.Identifier):
    """
    {
      id: "4136837",
      displayname: "Badwolfe",
      nickname: "Badwolfe",
      avatar:
        "https://robertsspaceindustries.com/media/rbj826kojz454r/heap_infobox/Wolf-Logo-Trans.png?v=1700823940",
      signature: "",
      meta: {
        badges: [
          {
            name: "High Admiral",
            icon: "https://media.robertsspaceindustries.com/i5zz45wyvg30r/heap_note.png",
          },
          {
            name: "PACK",
            icon: "https://cdn.robertsspaceindustries.com/static/images/organization/defaults/thumbnail/generic.png",
            url: "https://robertsspaceindustries.com/orgs/PCK",
          },
        ],
      },
      isGM: false,
      spoken_languages: [],
    }
    """

    def __init__(self, client: 'httpclient.HTTPClient', payload: dict):
        self._client = client
        self.id: int = int(payload["id"])
        self.displayname: str = payload["displayname"]
        self.nickname: str = payload["nickname"]
        self.avatar_url: str = payload["avatar"]
        self.signature: str = payload["signature"]
        self.isGM: bool = payload["isGM"]
        self.spoken_languages: list[str] = payload["spoken_languages"]
        self.meta: dict = payload["meta"]
        self.presence: Optional[Presence] = None
        self.badges: list[Badge] = [Badge(**badge) for badge in payload.get("badges")] if payload.get("badges") else []

        if "presence" in payload:
            self.presence = Presence(self._client, payload['presence'])

    def __repr__(self):
        return f"Member(id={repr(self.id)}, displayname={repr(self.displayname)}, nickname={repr(self.nickname)})"

    async def get_dm(self) -> 'lobby.Lobby':
        lobby = self._client.get_pm(self.id)
        if lobby:
            return lobby

        response = await self._client._http.fetch_lobby_info({"member_id": self.id})
        lobby = self._client._replace_lobby(response)
        return lobby

    async def send(self, content: str) -> 'message.Message':
        lobby = await self.get_dm()
        return await lobby.send(content)

    async def fetch_roles(self, community: 'community.Community'):
        await community.fetch_roles(self)

    async def fetch_counters(self, community: 'community.Community'):
        await community.fetch_counters(self)
