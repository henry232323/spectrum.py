import asyncio
import logging
import sys
from typing import Optional

from .http import HTTP
from .models import Lobby, Member, Community, Message, Forum, Channel, Thread, Reply, Role
from .util import register_callback, event_dispatch
from .util.event_dispatch import EventDispatchType
from .util.limited_size_dict import LimitedSizeDict

log = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.INFO)


@event_dispatch
class HTTPClient(EventDispatchType):
    def __init__(self, *, rsi_token: str = None, device_id: str = None, log_handler=log,
                 message_cache_size=500):
        self._http: HTTP = HTTP(self, rsi_token=rsi_token, device_id=device_id)
        self._ready_event = asyncio.Event()
        self._lobbies: dict[int, Lobby] = {}
        self._private_messages: dict[int, Lobby] = {}
        self._group_messages: dict[int, Lobby] = {}
        self._members: dict[int, Member] = {}
        self._messages: dict[int, Message] = LimitedSizeDict(size_limit=message_cache_size)
        self._communities: dict[int, Community] = {}
        self._forums: dict[int, Forum] = {}
        self._channels: dict[int, Channel] = {}
        self._threads: dict[int, Thread] = {}
        self._replies: dict[int, Reply] = {}
        self.log_handler = log_handler
        self.me: Optional[Member] = None

    def get_member(self, member_id: str | int) -> Optional[Member]:
        return self._members.get(int(member_id))

    @property
    def members(self) -> list[Member]:
        return list(self._members.values())

    def _replace_member(self, payload: dict):
        member = self.get_member(payload['id'])
        if member:
            member.__init__(self, payload)
        else:
            self._members[int(payload['id'])] = member = Member(self, payload)

        return member

    def get_lobby(self, lobby_id: str | int) -> Optional[Lobby]:
        return self._lobbies.get(int(lobby_id))

    @property
    def lobbies(self) -> list[Lobby]:
        return list(self._lobbies.values())

    @property
    def private_messages(self) -> dict[int, Lobby]:
        return self._private_messages.copy()

    def get_pm(self, id):
        return self._private_messages.get(int(id))

    @property
    def group_messages(self) -> list[Lobby]:
        return list(self._group_messages.values())

    def get_group_message(self, id):
        return self._group_messages.get(int(id))

    def _replace_lobby(self, payload: dict):
        lobby = self.get_lobby(payload['id'])
        if lobby:
            lobby.__init__(self, payload)
        else:
            self._lobbies[int(payload['id'])] = lobby = Lobby(self, payload)

        if lobby.type == "private":
            for member in lobby.members:
                if member.id != self.me.id:
                    self._private_messages[member.id] = lobby

        if lobby.type == "group":
            for member in lobby.members:
                if member.id != self.me.id:
                    self._group_messages[lobby.id] = lobby

        return lobby

    def get_community(self, community_id: int | str) -> Optional[Community]:
        return self._communities.get(int(community_id))

    @property
    def communities(self) -> list[Community]:
        return list(self._communities.values())

    def _replace_community(self, payload: dict):
        community = self.get_community(payload['id'])
        if community:
            community.__init__(self, payload)
        else:
            self._communities[int(payload['id'])] = community = Community(self, payload)

        return community

    def get_forum(self, forum_id: str | int) -> Optional[Forum]:
        return self._forums.get(int(forum_id))

    @property
    def forums(self) -> list[Forum]:
        return list(self._forums.values())

    def _replace_forum(self, payload: dict):
        forum = self.get_forum(payload['id'])
        if forum:
            forum.__init__(self, payload)
        else:
            self._forums[int(payload['id'])] = forum = Forum(self, payload)

        return forum

    def get_channel(self, channel_id: str | int) -> Optional[Channel]:
        return self._channels.get(int(channel_id))

    @property
    def channels(self) -> list[Channel]:
        return list(self._channels.values())

    def _replace_channel(self, payload: dict):
        channel = self.get_channel(payload['id'])
        if channel:
            channel.__init__(self, payload)
        else:
            self._channels[int(payload['id'])] = channel = Channel(self, payload)

        return channel

    def get_thread(self, thread_id: str | int) -> Optional[Thread]:
        return self._threads.get(int(thread_id))

    @property
    def threads(self) -> list[Thread]:
        return list(self._threads.values())

    def _replace_thread(self, payload: dict):
        thread = self.get_thread(int(payload['id']))
        if thread:
            thread.__init__(self, payload)
        else:
            self._threads[int(payload['id'])] = thread = Thread(self, payload)

        return thread

    def get_message(self, message_id: str | int) -> Optional[Message]:
        return self._messages.get(int(message_id))

    @property
    def messages(self) -> list[Message]:
        return list(self._messages.values())

    def _replace_message(self, payload: dict):
        message = self.get_message(int(payload['id']))
        if message:
            message.__init__(self, payload)
        else:
            self._messages[int(payload['id'])] = message = Message(self, payload)

        return message

    def get_reply(self, reply_id: str | int) -> Optional[Reply]:
        return self._replies.get(int(reply_id))

    @property
    def replies(self) -> list[Reply]:
        return list(self._replies.values())

    def _replace_reply(self, payload: dict):
        reply = self.get_reply(payload['id'])
        if reply:
            reply.__init__(self, payload)
        else:
            self._replies[int(payload['id'])] = reply = Reply(self, payload)

        return reply

    @property
    def roles(self) -> list[Role]:
        return [r for community in self._communities.values() for r in community.roles]

    async def sink_threads(self, *threads):
        return await self._http.sink_threads({
            "thread_ids": [t.id for t in threads]
        })

    async def pin_threads(self, *threads):
        return await self._http.pin_threads({
            "thread_ids": [t.id for t in threads]
        })

    async def close_threads(self, *threads, reason: str = None):
        return await self._http.close_threads({
            "thread_ids": [t.id for t in threads],
            "reason": reason
        })

    async def delete_threads(self, *threads, reason: str = None):
        return await self._http.delete_threads({
            "thread_ids": [t.id for t in threads],
            "reason": reason
        })

    async def fetch_lobby(self, lobby_id):
        payload = await self._http.fetch_lobby_info(dict(lobby_id=lobby_id))
        lobby = self._replace_lobby(payload)
        return lobby

    async def fetch_member_by_id(self, member_id):
        payload = await self._http.fetch_member_by_id(dict(member_id=member_id))
        member = self._replace_member(payload['member'])
        return member

    async def fetch_member_by_handle(self, handle):
        payload = await self._http.fetch_member_by_handle(dict(nickname=handle))
        member = self._replace_member(payload['member'])
        return member

    async def search_users(self, query: str, ignore_self=True, community=None, max_count=None):
        """Used when adding friends."""
        page = 1
        count = 0
        while True:
            payload = await self._http.search_users({
                "community_id": community.id if community else None,
                "text": query,
                "ignore_self": ignore_self,
                "pagesize": 15,  # maximum page size
                "page": page,
            })

            page = payload['page'] + 1

            for member in payload['members']:
                yield self._replace_member(member)
                count += 1

                if count >= max_count:
                    return

            if payload['page'] >= payload['pages_total']:
                return

    @register_callback('identify')
    async def _on_identify_raw(self, payload):
        if payload.get("member"):
            self.me = self._replace_member(payload["member"])

        if payload.get("friends"):
            for friend in payload["friends"] or []:
                self._replace_member(friend)

        communities = payload.get("communities", [])
        group_lobbies = payload.get("group_lobbies", [])
        private_lobbies = payload.get("private_lobbies", [])
        for community in communities or []:
            self._replace_community(community)

        for lpayload in group_lobbies or []:
            self._replace_lobby(lpayload)

        for lpayload in private_lobbies or []:
            self._replace_lobby(lpayload)

        self._ready_event.set()

    async def identify(self):
        return await self._http.identify()

    async def close(self):
        await self._http.close()
