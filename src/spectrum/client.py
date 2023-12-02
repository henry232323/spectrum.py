import asyncio
import logging
import traceback

from .gateway import Gateway
from .http import HTTP
from .models import Object
from .models.channel import Channel
from .models.community import Community
from .models.forum import Forum
from .models.lobby import Lobby
from .models.member import Member
from .models.message import Message
from .models.presence import Presence
from .models.reply import Reply
from .models.role import Role
from .models.thread import Thread
from .util import find


class Client:
    def __init__(self, *, token: str = None, device_id: str = None, log_handler=logging.getLogger('spectrum.py')):
        self._ready_event = asyncio.Event()
        self._lobbies: dict[int, Lobby] = {}
        self._members: dict[int, Member] = {}
        self._communities: dict[int, Community] = {}
        self._forums: dict[int, Forum] = {}
        self._channels: dict[int, Channel] = {}
        self._threads: dict[int, Thread] = {}
        self._replies: dict[int, Reply] = {}
        self._gateway: Gateway = Gateway(client=self, token=token, device_id=device_id)
        self._http: HTTP = HTTP(self._gateway, token=token)
        self.log_handler = log_handler
        self.me: Member | None = None

    async def run(self):
        try:
            await self._gateway.start()
        except Exception as e:
            traceback.print_exc()

    def get_member(self, member_id: str | int) -> Lobby | None:
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

    def get_lobby(self, lobby_id: str | int) -> Lobby | None:
        return self._lobbies.get(int(lobby_id))

    @property
    def lobbies(self) -> list[Lobby]:
        return list(self._lobbies.values())

    def _replace_lobby(self, payload: dict):
        lobby = self.get_lobby(payload['id'])
        if lobby:
            lobby.__init__(self, payload)
        else:
            self._lobbies[int(payload['id'])] = lobby = Lobby(self, payload)

        return lobby

    def get_community(self, community_id: int | str) -> Community | None:
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

    def get_forum(self, forum_id: str | int) -> Forum | None:
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

    def get_channel(self, channel_id: str | int) -> Channel | None:
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

    def get_thread(self, thread_id: str | int) -> Thread | None:
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

    def get_reply(self, reply_id: str | int) -> Reply | None:
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

    async def _on_message_raw(self, payload: dict):
        self._replace_member(payload['message']['member'])
        asyncio.create_task(self.on_message(Message(self, payload)))

    async def on_message(self, message: Message):
        pass

    async def _on_identify_raw(self, payload):
        if payload.get("member"):
            self.me = self._replace_member(payload["member"])

        if payload.get("friends"):
            for friend in payload["friends"] or []:
                self._replace_member(friend)

    async def _on_ready_raw(self, payload):
        self._ready_event.set()
        asyncio.create_task(self.on_ready())

    async def on_ready(self):
        pass

    async def _on_presence_update_raw(self, payload):
        # {"type": "member.presence.update", "member_id": 2280259}
        member = self.get_member(payload["member_id"])
        if member:
            member.presence = presence = Presence(self, payload["presence"])
            asyncio.create_task(self.on_presence_update(member, presence))

    async def on_presence_update(self, member, presence: Presence):
        pass

    async def _on_presence_join_raw(self, payload):
        member = self.get_member(payload["member_id"])
        if member:
            member.presence = presence = Presence(self, payload['member']['presence'])
            asyncio.create_task(self.on_presence_join(member, presence))

    async def on_presence_join(self, member, presence):
        pass

    async def _on_forum_thread_reply_raw(self, payload):
        # {"type":"forum.thread.reply.new","channel_id":3,"label_id":null,"thread_id":396187,"reply_id":6452134}
        thread = self.get_thread(payload["thread_id"])
        if not thread:
            response = await self._http.fetch_thread_nested(
                {"thread_id": payload["thread_id"], "sort": "votes", "target_reply_id": payload["reply_id"]})

            thread.replies.append(self._replace_reply(response["data"]))

        reply = find(thread.replies, payload["reply_id"])
        asyncio.create_task(self.on_forum_thread_reply(reply))

    async def on_forum_thread_reply(self, reply):
        pass

    async def _on_forum_thread_new_raw(self, payload):
        # {"type":"forum.thread.new","channel_id":3,"thread_id":396233,"label_id":null,"time_created":1701340775}
        response = await self._http.fetch_thread_nested(
            {"thread_id": payload["thread_id"], "sort": "votes", "target_reply_id": None})
        thread = self._replace_thread(response["data"])
        asyncio.create_task(self.on_forum_thread_new(thread))

    async def on_forum_thread_new(self, thread):
        pass

    async def _on_member_roles_update_raw(self, payload):
        # {"type": "member.roles.update", "community_id": 1, "member_id": 15013, "roles": ["11", "12", "4", "5", "6"]}
        community = self.get_community(payload['community_id'])
        member = self.get_community(payload['member_id'])
        if not member:
            member = Object(self, id=payload['member_id'])

        if community:
            roles = []
            for item in payload['roles']:
                role = community.get_role(item)
                roles.append(role)

            asyncio.create_task(self.on_member_roles_update(community, member, roles))
        else:
            self.log_handler.error("Failed to handle role update", payload)

    async def on_member_roles_update(self, community, member, roles):
        pass

    async def subscribe_to_topic(self, *subscription_keys):
        await self._gateway.subscribe_to_key(*subscription_keys)

    async def fetch_member_by_id(self, member_id):
        payload = await self._http.fetch_member_by_id(dict(member_id=member_id))
        member = self._replace_member(payload['data'])
        return member

    async def fetch_member_by_handle(self, handle):
        payload = await self._http.fetch_member_by_handle(dict(nickname=handle))
        member = self._replace_member(payload['data'])
        return member
