import asyncio
import traceback

from .gateway import Gateway
from .httpclient import HTTPClient
from .models import Object
from .models.lobby import Lobby
from .models.member import Member
from .models.message import Message
from .models.presence import Presence
from .models.reaction import Reaction
from .util import find, event_dispatch, register_callback
from .util.event_dispatch import EventDispatchType


@event_dispatch
class Client(HTTPClient, EventDispatchType):
    def __init__(self, *, rsi_token: str = None, device_id: str = None, **kwargs):
        super().__init__(rsi_token=rsi_token, device_id=device_id, **kwargs)
        self._gateway: Gateway = Gateway(client=self, rsi_token=rsi_token, device_id=device_id)

    async def run(self):
        gateway_token = await self.identify()
        try:
            await self._gateway.start(gateway_token)
        except Exception as e:
            traceback.print_exc()

    @register_callback('message.new')
    async def _on_message_raw(self, payload: dict):
        self._replace_member(payload['message']['member'])
        message = self._replace_message(payload['message'])
        asyncio.create_task(self.on_message(message))

    async def on_message(self, message: Message):
        pass

    @register_callback('message.edit')
    async def _on_message_edit_raw(self, payload: dict):
        self._replace_member(payload['message']['member'])
        message = self._replace_message(payload['message'])
        asyncio.create_task(self.on_message_edit(message))

    async def on_message_edit(self, message: Message):
        pass

    @register_callback('member.update')
    async def _on_member_update_raw(self, payload: dict):
        member = self._replace_member(payload['member'])
        asyncio.create_task(self.on_member_update(member))

    async def on_member_update(self, member: Member):
        pass

    @register_callback('broadcaster.ready')
    async def _on_ready_raw(self, payload):
        asyncio.create_task(self.on_ready())

    async def on_ready(self):
        pass

    @register_callback('member.presence.update')
    async def _on_presence_update_raw(self, payload):
        # {"type": "member.presence.update", "member_id": 2280259}
        member = self.get_member(payload["member_id"])
        if member:
            member.presence = presence = Presence(self, payload["presence"])
            asyncio.create_task(self.on_presence_update(member, presence))

    async def on_presence_update(self, member, presence: Presence):
        pass

    @register_callback('message_lobby.presence.join')
    async def _on_presence_join_raw(self, payload):
        member = self.get_member(payload["member_id"])
        if member:
            member.presence = presence = Presence(self, payload['member']['presence'])
            asyncio.create_task(self.on_presence_join(member, presence))

    async def on_presence_join(self, member, presence):
        pass

    @register_callback('message_lobby.presence.leave')
    async def _on_presence_leave_raw(self, payload):
        member = self.get_member(payload["member_id"])
        if member:
            member.presence = None
            asyncio.create_task(self.on_presence_leave(member))

    async def on_presence_leave(self, member):
        pass

    @register_callback('reaction.add')
    async def _on_reaction_add_raw(self, payload):
        member = self.get_member(payload["reaction"]["member"]["id"])
        if member:
            asyncio.create_task(self.on_reaction_add(member, reaction=Reaction(self, payload['reaction'])))

    async def on_reaction_add(self, member: Member, reaction: Reaction):
        pass

    @register_callback('reaction.remove')
    async def _on_reaction_remove_raw(self, payload):
        member = self.get_member(payload["reaction"]["member"]["id"])
        if member:
            asyncio.create_task(self.on_reaction_remove(member, reaction=Reaction(self, payload['reaction'])))

    async def on_reaction_remove(self, member: Member, reaction: Reaction):
        pass

    @register_callback('message_lobby.typing.end')
    async def _on_typing_end_raw(self, payload):
        member = self.get_member(payload["member_id"])
        lobby = self.get_lobby(payload["lobby_id"])
        if member and lobby:
            asyncio.create_task(self.on_typing_end(lobby, member))

    async def on_typing_end(self, lobby: Lobby, member: Member):
        pass

    @register_callback('message_lobby.typing.start')
    async def _on_typing_start_raw(self, payload):
        member = self.get_member(payload["member_id"])
        lobby = self.get_lobby(payload["lobby_id"])
        if member and lobby:
            asyncio.create_task(self.on_typing_start(lobby, member))

    async def on_typing_start(self, lobby: Lobby, member: Member):
        pass

    async def _on_forum_thread_reply_raw(self, payload):
        # {"type":"forum.thread.reply.new","channel_id":3,"label_id":null,"thread_id":396187,"reply_id":6452134}
        thread = self.get_thread(payload["thread_id"])
        if not thread:
            response = await self._http.fetch_thread_nested(
                {"thread_id": payload["thread_id"], "sort": "votes", "target_reply_id": payload["reply_id"]}
            )

            thread.replies.append(self._replace_reply(response))

        reply = find(thread.replies, payload["reply_id"])
        asyncio.create_task(self.on_forum_thread_reply(reply))

    async def on_forum_thread_reply(self, reply):
        pass

    @register_callback('thread.new')
    async def _on_forum_thread_new_raw(self, payload):
        # {"type":"forum.thread.new","channel_id":3,"thread_id":396233,"label_id":null,"time_created":1701340775}
        response = await self._http.fetch_thread_nested(
            {"thread_id": payload["thread_id"], "sort": "votes", "target_reply_id": None})
        thread = self._replace_thread(response)
        await self.subscribe_to_topic(thread.subscription_key)
        asyncio.create_task(self.on_forum_thread_new(thread))

    async def on_forum_thread_new(self, thread):
        pass

    @register_callback('forum_channel.new')
    async def _on_channel_new_raw(self, payload: dict):
        # {"type":"forum_channel.new","action_id":null,"forum_channel":{"id":335897,"time_created":"2023-12-05 05:12:38","time_modified":"2023-12-05 05:12:38","community_id":100987,"name":"Test Channel 5","description":"asdasd","color":"FF6262","order":4,"group_id":102761,"sort_filter":null,"label_required":false},"owner":true}
        channel = self._replace_channel(payload["forum_channel"])
        await self.subscribe_to_topic(channel.subscription_key, *(labels.subscription_key for labels in channel.labels))
        asyncio.create_task(self.on_channel_new(channel))

    async def on_channel_new(self, channel):
        pass

    @register_callback('forum_channel.remove')
    async def _on_channel_remove_raw(self, payload: dict):
        # {"type":"forum_channel.remove","action_id":null,"forum_channel_id":"335898","owner":true}
        channel = self._channels.pop(int(payload["forum_channel_id"]))
        asyncio.create_task(self.on_channel_remove(channel))

    async def on_channel_remove(self, channel):
        pass

    @register_callback('member.roles.update')
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
            self.log_handler.error(f"Failed to handle role update: {community} {member} {payload}")

    async def on_member_roles_update(self, community, member, roles):
        pass

    @register_callback("unhandled_event")
    async def _on_unhandled_event_raw(self, payload):
        self.log_handler.info("Received unhandled event of type %s: %s", payload['type'], payload)
        asyncio.create_task(self.on_unhandled_event(payload))

    async def on_unhandled_event(self, payload):
        pass

    async def subscribe_to_topic(self, *subscription_keys):
        await self._gateway.subscribe_to_key(*subscription_keys)

    async def subscribe_to_all(self):
        """Subscribe to all lobbies, threads, and channels to receive message/reply events."""
        keys = []
        for lobby in self.lobbies:
            keys.append(lobby.subscription_key)

        for thread in self.threads:
            keys.append(thread.subscription_key)

        for channel in self.channels:
            keys.append(channel.subscription_key)
            for label in channel.labels:
                keys.append(label.subscription_key)

        await self.subscribe_to_topic(*keys)

    async def subscribe_to_default(self):
        """Subscribe to the default set of topics, including the public SC community and all direct messages and group messages."""
        keys = []
        for lobby in self.group_messages or []:
            keys.append(lobby.subscription_key)

        for lobby in self.private_messages.values():
            keys.append(lobby.subscription_key)

        main_community = self.get_community(1)
        if main_community:
            for lobby in main_community.lobbies:
                keys.append(lobby.subscription_key)

        await self.subscribe_to_topic(*keys)

    def _replace_lobby(self, payload: dict):
        lobby = super()._replace_lobby(payload)
        asyncio.create_task(lobby.fetch_presence())
        return lobby
