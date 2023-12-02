import asyncio
import traceback

from .gateway import Gateway
from .http import HTTP
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
    def __init__(self, *, token: str = None, device_id: str = None):
        self._ready_event = asyncio.Event()
        self._lobbies: dict[str, Lobby] = {}
        self._members: dict[str, Member] = {}
        self._communities: dict[str, Community] = {}
        self._forums: dict[str, Forum] = {}
        self._channels: dict[str, Channel] = {}
        self._threads: dict[str, Thread] = {}
        self._replies: dict[str, Reply] = {}
        self._roles: dict[str, Role] = {}
        self._gateway: Gateway = Gateway(client=self, token=token, device_id=device_id)
        self._http: HTTP = HTTP(self._gateway, token=token)
        self.me: Member | None = None

    async def run(self):
        try:
            await self._gateway.start()
        except Exception as e:
            traceback.print_exc()

    def get_member(self, member_id: str) -> Lobby | None:
        return self._members.get(member_id)

    @property
    def members(self) -> list[Member]:
        return list(self._members.values())

    def _replace_member(self, payload: dict):
        member = self._members.get(payload['id'])
        if member:
            member.__init__(self, payload)
        else:
            self._members[payload['id']] = member = Member(self, payload)

        return member

    def get_lobby(self, lobby_id: str) -> Lobby | None:
        return self._lobbies.get(lobby_id)

    @property
    def lobbies(self) -> list[Lobby]:
        return list(self._lobbies.values())

    def _replace_lobby(self, payload: dict):
        lobby = self._lobbies.get(payload['id'])
        if lobby:
            lobby.__init__(self, payload)
        else:
            self._lobbies[payload['id']] = lobby = Lobby(self, payload)

        return lobby

    def get_community(self, community_id: str) -> Community | None:
        return self._communities.get(community_id)

    @property
    def communities(self) -> list[Community]:
        return list(self._communities.values())

    def _replace_community(self, payload: dict):
        community = self._communities.get(payload['id'])
        if community:
            community.__init__(self, payload)
        else:
            self._communities[payload['id']] = community = Community(self, payload)

        return community

    def get_forum(self, forum_id: str) -> Forum | None:
        return self._forums.get(forum_id)

    @property
    def forums(self) -> list[Forum]:
        return list(self._forums.values())

    def _replace_forum(self, payload: dict):
        forum = self._forums.get(payload['id'])
        if forum:
            forum.__init__(self, payload)
        else:
            self._forums[payload['id']] = forum = Forum(self, payload)

        return forum

    def get_channel(self, channel_id: str) -> Channel | None:
        return self._channels.get(channel_id)

    @property
    def channels(self) -> list[Channel]:
        return list(self._channels.values())

    def _replace_channel(self, payload: dict):
        channel = self._channels.get(payload['id'])
        if channel:
            channel.__init__(self, payload)
        else:
            self._channels[payload['id']] = channel = Channel(self, payload)

        return channel

    def get_thread(self, thread_id: str) -> Thread | None:
        return self._threads.get(thread_id)

    @property
    def threads(self) -> list[Thread]:
        return list(self._threads.values())

    def _replace_thread(self, payload: dict):
        thread = self._threads.get(payload['id'])
        if thread:
            thread.__init__(self, payload)
        else:
            self._threads[payload['id']] = thread = Thread(self, payload)

        return thread

    def get_reply(self, reply_id: str) -> Reply | None:
        return self._replies.get(reply_id)

    @property
    def replies(self) -> list[Reply]:
        return list(self._replies.values())

    def _replace_reply(self, payload: dict):
        reply = self._replies.get(payload['id'])
        if reply:
            reply.__init__(self, payload)
        else:
            self._replies[payload['id']] = reply = Reply(self, payload)

        return reply

    def get_role(self, role_id: str) -> Role | None:
        return self._replies.get(role_id)

    @property
    def roles(self) -> list[Role]:
        return list(self._roles.values())

    def _replace_role(self, payload: dict):
        role = self._roles.get(payload['id'])
        if role:
            role.__init__(self, payload)
        else:
            self._roles[payload['id']] = role = Role(self, payload)

        return role

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
            member.presence = presence = Presence(self, payload['presence'])
            asyncio.create_task(self.on_presence_join(member, presence))

    async def on_presence_join(self, member, presence):
        pass

    async def _on_forum_thread_reply_raw(self, payload):
        # {"type":"forum.thread.reply.new","channel_id":3,"label_id":null,"thread_id":396187,"reply_id":6452134}
        thread = self.get_thread(payload["thread_id"])
        if not thread:
            response = await self._http.fetch_thread(
                {"thread_id": payload["thread_id"], "sort": "votes", "target_reply_id": payload["reply_id"]})

            thread.replies.append(self._replace_reply(response["data"]))

        reply = find(thread.replies, payload["reply_id"])
        asyncio.create_task(self.on_forum_thread_reply(reply))

    async def on_forum_thread_reply(self, reply):
        pass

    async def _on_forum_thread_new_raw(self, payload):
        # {"type":"forum.thread.new","channel_id":3,"thread_id":396233,"label_id":null,"time_created":1701340775}
        response = await self._http.fetch_thread(
            {"thread_id": payload["thread_id"], "sort": "votes", "target_reply_id": None})
        thread = self._replace_thread(response["data"])
        asyncio.create_task(self._on_forum_thread_new(thread))

    async def _on_forum_thread_new(self, thread):
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
