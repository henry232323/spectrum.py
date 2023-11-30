import asyncio
import traceback

from .gateway import Gateway
from .http import HTTP
from .models.community import Community
from .models.lobby import Lobby
from .models.member import Member
from .models.message import Message


class Client:
    def __init__(self, *, token: str = None, device_id: str = None):
        self._ready_event = asyncio.Event()
        self._lobbies: dict[str, Lobby] = {}
        self._members: dict[str, Member] = {}
        self._communities: dict[str, Community] = {}
        self._gateway = Gateway(client=self, token=token, device_id=device_id)
        self._http = HTTP(self._gateway, token=token)

    async def run(self):
        try:
            await self._gateway.start()
        except Exception as e:
            traceback.print_exc()

    def get_lobby(self, lobby_id: str) -> Lobby | None:
        return self._lobbies.get(lobby_id)

    @property
    def lobbies(self) -> list[Lobby]:
        return list(self._lobbies.values())

    def get_member(self, member_id: str) -> Lobby | None:
        return self._members.get(member_id)

    @property
    def members(self) -> list[Member]:
        return list(self._members.values())

    def get_community(self, community_id: str) -> Community | None:
        return self._communities.get(community_id)

    @property
    def communities(self) -> list[Community]:
        return list(self._communities.values())

    def _replace_member(self, payload: dict):
        member = self._members.get(payload['id'])
        if member:
            member.__init__(self, payload)
        else:
            self._members[payload['id']] = member = Member(self, payload)

        return member

    def _replace_lobby(self, payload: dict):
        lobby = self._lobbies.get(payload['id'])
        if lobby:
            lobby.__init__(self, payload)
        else:
            self._lobbies[payload['id']] = lobby = Lobby(self, payload)

        return lobby

    def _replace_community(self, payload: dict):
        community = self._communities.get(payload['id'])
        if community:
            community.__init__(self, payload)
        else:
            self._communities[payload['id']] = community = Community(self, payload)

        return community

    async def _on_message_raw(self, payload: dict):
        self._replace_member(payload['message']['member'])
        asyncio.create_task(self.on_message(Message(self, payload)))

    async def on_message(self, message: Message):
        pass

    async def _on_ready_raw(self, payload):
        self._ready_event.set()
        asyncio.create_task(self.on_ready())

    async def on_ready(self):
        pass
