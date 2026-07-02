from __future__ import annotations

import asyncio
import traceback
from typing import TYPE_CHECKING

from .gateway import Gateway
from .httpclient import HTTPClient
from .models import Object
from .models.channel import Channel
from .models.lobby import Lobby
from .models.member import Member
from .models.message import Message
from .models.presence import Presence
from .models.reaction import Reaction
from .models.reply import Reply
from .models.thread import Thread, ThreadStub
from .models.upload import Upload
from .util import find, event_dispatch, register_callback
from .util.event_dispatch import EventDispatchType

if TYPE_CHECKING:
    from .models.community import Community
    from .models.role import Role


@event_dispatch
class Client(HTTPClient, EventDispatchType):
    def __init__(self, *, rsi_token: str = None, device_id: str = None, **kwargs):
        super().__init__(rsi_token=rsi_token, device_id=device_id, **kwargs)
        self._gateway: Gateway = Gateway(client=self, rsi_token=rsi_token, device_id=device_id)
        self._media_ready_events: dict[str, asyncio.Event] = {}

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
        asyncio.ensure_future(self.on_message(message))

    async def on_message(self, message: Message):
        pass

    @register_callback('message.edit')
    async def _on_message_edit_raw(self, payload: dict):
        self._replace_member(payload['message']['member'])
        message = self._replace_message(payload['message'])
        asyncio.ensure_future(self.on_message_edit(message))

    async def on_message_edit(self, message: Message):
        pass

    @register_callback('member.update')
    async def _on_member_update_raw(self, payload: dict):
        member = self._replace_member(payload['member'])
        asyncio.ensure_future(self.on_member_update(member))

    async def on_member_update(self, member: Member):
        pass

    @register_callback('broadcaster.ready')
    async def _on_ready_raw(self, payload):
        asyncio.ensure_future(self.on_ready())

    async def on_ready(self):
        pass

    @register_callback('member.presence.update')
    async def _on_presence_update_raw(self, payload):
        member = self.get_member(payload["member_id"])
        if member:
            member.presence = presence = Presence(self, payload["presence"])
            asyncio.ensure_future(self.on_presence_update(member, presence))

    async def on_presence_update(self, member, presence: Presence):
        pass

    @register_callback('message_lobby.presence.join')
    async def _on_presence_join_raw(self, payload):
        member = self._replace_member(payload['member'])
        member.presence = presence = Presence(self, payload['member']['presence'])
        asyncio.ensure_future(self.on_presence_join(member, presence))

    async def on_presence_join(self, member, presence):
        pass

    @register_callback('message_lobby.presence.leave')
    async def _on_presence_leave_raw(self, payload):
        member = self.get_member(payload["member_id"])
        if member:
            member.presence = None
            asyncio.ensure_future(self.on_presence_leave(member))

    async def on_presence_leave(self, member):
        pass

    @register_callback('reaction.add')
    async def _on_reaction_add_raw(self, payload):
        member = self._replace_member(payload["reaction"]["member"])
        asyncio.ensure_future(self.on_reaction_add(member, reaction=Reaction(self, payload['reaction'])))

    async def on_reaction_add(self, member: Member, reaction: Reaction):
        pass

    @register_callback('reaction.remove')
    async def _on_reaction_remove_raw(self, payload):
        member = self._replace_member(payload["reaction"]["member"])
        asyncio.ensure_future(self.on_reaction_remove(member, reaction=Reaction(self, payload['reaction'])))

    async def on_reaction_remove(self, member: Member, reaction: Reaction):
        pass

    @register_callback('message_lobby.typing.end')
    async def _on_typing_end_raw(self, payload):
        member = self.get_member(payload["member_id"])
        lobby = self.get_lobby(payload["lobby_id"])
        if member and lobby:
            asyncio.ensure_future(self.on_typing_end(lobby, member))

    async def on_typing_end(self, lobby: Lobby, member: Member):
        pass

    @register_callback('message_lobby.typing.start')
    async def _on_typing_start_raw(self, payload):
        member = self.get_member(payload["member_id"])
        lobby = self.get_lobby(payload["lobby_id"])
        if member and lobby:
            asyncio.ensure_future(self.on_typing_start(lobby, member))

    async def on_typing_start(self, lobby: Lobby, member: Member):
        pass

    @register_callback('forum.thread.reply.new')
    async def _on_forum_thread_reply_raw(self, payload):
        # {"type":"forum.thread.reply.new","channel_id":3,"label_id":null,"thread_id":396187,"reply_id":6452134}
        thread = self.get_thread(payload["thread_id"])
        if not thread:
            thread = self.get_thread_stub(payload['thread_id'])
            if not thread:
                channel = self.get_channel(payload['channel_id'])
                await channel.fetch_thread_stubs()
                thread = self.get_thread_stub(payload['thread_id'])

            if not thread:
                return


        response = await self._http.fetch_thread_nested(
            {"slug": thread.slug, "sort": "votes", "target_reply_id": payload["reply_id"]}
        )
        thread = self._replace_thread(response)

        reply = find(thread.replies, payload["reply_id"])
        asyncio.ensure_future(self.on_forum_thread_reply(reply))

    async def on_forum_thread_reply(self, reply):
        pass

    @register_callback('thread.new')
    async def _on_forum_thread_new_raw(self, payload):
        # {"type":"forum.thread.new","channel_id":3,"thread_id":396233,"label_id":null,"time_created":1701340775}
        response = await self._http.fetch_thread_nested(
            {"slug": payload["slug"], "sort": "votes", "target_reply_id": None})
        thread = self._replace_thread(response)
        await self.subscribe_to_topic(thread.subscription_key)
        asyncio.ensure_future(self.on_forum_thread_new(thread))

    async def on_forum_thread_new(self, thread):
        pass

    @register_callback('forum_channel.new')
    async def _on_channel_new_raw(self, payload: dict):
        # {"type":"forum_channel.new","action_id":null,"forum_channel":{"id":335897,"time_created":"2023-12-05 05:12:38","time_modified":"2023-12-05 05:12:38","community_id":100987,"name":"Test Channel 5","description":"asdasd","color":"FF6262","order":4,"group_id":102761,"sort_filter":null,"label_required":false},"owner":true}
        channel = self._replace_channel(payload["forum_channel"])
        await self.subscribe_to_topic(channel.subscription_key, *(labels.subscription_key for labels in channel.labels))
        asyncio.ensure_future(self.on_channel_new(channel))

    async def on_channel_new(self, channel):
        pass

    @register_callback('forum_channel.remove')
    async def _on_channel_remove_raw(self, payload: dict):
        # {"type":"forum_channel.remove","action_id":null,"forum_channel_id":"335898","owner":true}
        channel = self._channels.pop(int(payload["forum_channel_id"]))
        asyncio.ensure_future(self.on_channel_remove(channel))

    async def on_channel_remove(self, channel):
        pass

    @register_callback('member.roles.update')
    async def _on_member_roles_update_raw(self, payload):
        # {"type": "member.roles.update", "community_id": 1, "member_id": 15013, "roles": ["11", "12", "4", "5", "6"]}
        community = self.get_community(payload['community_id'])
        member = self.get_member(payload['member_id'])
        if not member:
            member = Object(self, id=payload['member_id'])

        if community:
            roles = []
            for item in payload['roles']:
                role = community.get_role(item)
                roles.append(role)

            asyncio.ensure_future(self.on_member_roles_update(community, member, roles))
        else:
            self.log_handler.error(f"Failed to handle role update: {community} {member} {payload}")

    async def on_member_roles_update(self, community, member, roles):
        pass

    @register_callback('media.processing.ready')
    async def _on_media_processing_ready_raw(self, payload):
        media_data = payload.get('media', {})
        upload = Upload(media_data)
        self._media_ready_events.setdefault(upload.id, asyncio.Event()).set()
        asyncio.ensure_future(self.on_media_ready(upload))

    async def on_media_ready(self, upload: Upload):
        """Called when an uploaded image finishes processing."""
        pass

    @register_callback('message_lobby.read.update')
    async def _on_lobby_read_update_raw(self, payload):
        lobby = self.get_lobby(payload.get('lobby_id')) or Object(self, id=payload.get('lobby_id'))
        message = self.get_message(payload.get('message_id')) or Object(self, id=payload.get('message_id'))
        asyncio.ensure_future(self.on_lobby_read_update(lobby, message))

    async def on_lobby_read_update(self, lobby: Lobby | Object, message: Message | Object):
        """Called when read marker updates in a lobby."""
        pass

    @register_callback('forum.thread.read.update')
    async def _on_thread_read_update_raw(self, payload):
        thread_id = int(payload.get('thread_id', 0))
        thread = self.get_thread(thread_id) or self.get_thread_stub(thread_id) or Object(self, id=thread_id)
        reply = self.get_reply(payload.get('reply_id')) or Object(self, id=payload.get('reply_id'))
        asyncio.ensure_future(self.on_thread_read_update(thread, reply))

    async def on_thread_read_update(self, thread: Thread | ThreadStub | Object, reply: Reply | Object):
        """Called when read marker updates in a thread."""
        pass

    @register_callback('forum.channel.read.update')
    async def _on_channel_read_update_raw(self, payload):
        channel_id = int(payload.get('channel_id', 0))
        thread_id = int(payload.get('thread_id', 0))
        channel = self.get_channel(channel_id) or Object(self, id=channel_id)
        thread = self.get_thread(thread_id) or self.get_thread_stub(thread_id) or Object(self, id=thread_id)
        asyncio.ensure_future(self.on_channel_read_update(channel, thread))

    async def on_channel_read_update(self, channel: Channel | Object, thread: Thread | ThreadStub | Object):
        """Called when read marker updates in a forum channel."""
        pass

    @register_callback('notification.subscription.update')
    async def _on_notification_subscription_update_raw(self, payload):
        entity_type = payload.get('entity_type')
        entity_id = payload.get('entity_id')
        entity: Thread | ThreadStub | Channel | Lobby | Object
        if entity_type == 'forum_thread':
            entity = self.get_thread(entity_id) or self.get_thread_stub(entity_id) or Object(self, id=entity_id)
        elif entity_type == 'forum_channel':
            entity = self.get_channel(entity_id) or Object(self, id=entity_id)
        elif entity_type == 'message_lobby':
            entity = self.get_lobby(entity_id) or Object(self, id=entity_id)
        else:
            entity = Object(self, id=entity_id)
        asyncio.ensure_future(self.on_notification_subscription_update(entity_type, entity, payload.get('subscription_type')))

    async def on_notification_subscription_update(self, entity_type: str, entity: Thread | ThreadStub | Channel | Lobby | Object, subscription_type: str):
        """Called when notification subscription changes (e.g. auto-subscribe to created thread)."""
        pass

    @register_callback('friendship.init_presences')
    async def _on_friendship_init_presences_raw(self, payload):
        presences: dict[Member | Object, list | None] = {}
        for member_id, presence_data in payload.get('presences', {}).items():
            member = self.get_member(member_id) or Object(self, id=member_id)
            presences[member] = presence_data
        asyncio.ensure_future(self.on_friendship_init_presences(presences))

    async def on_friendship_init_presences(self, presences: dict[Member | Object, list | None]):
        """Called on connect with initial friend presence states."""
        pass

    @register_callback('client.version')
    async def _on_client_version_raw(self, payload):
        pass

    @register_callback("unhandled_event")
    async def _on_unhandled_event_raw(self, payload):
        self.log_handler.info("Received unhandled event of type %s: %s", payload['type'], payload)
        asyncio.ensure_future(self.on_unhandled_event(payload))

    async def on_unhandled_event(self, payload):
        pass

    async def upload_image(self, file_path: str, filename: str = None, content_type: str = None, wait: bool = True, timeout: float = 30) -> Upload:
        """Upload an image and optionally wait for processing via gateway event. Set wait=False to return immediately."""
        upload = await super().upload_image(file_path, filename=filename, content_type=content_type)
        if wait and upload.processing:
            await self.wait_for_media(upload, timeout=timeout)
            upload.processing = False
        return upload

    async def wait_for_media(self, upload: Upload = None, *, upload_id: str = None, timeout: float = 30) -> bool:
        """Wait for an uploaded image to finish processing via gateway event. Returns True if ready, False on timeout."""
        _id = upload.id if upload else upload_id
        if not _id:
            raise ValueError("Provide either upload or upload_id")
        event = self._media_ready_events.setdefault(_id, asyncio.Event())
        if event.is_set():
            return True
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False

    async def subscribe_to_topic(self, *subscription_keys, scope=None):
        await self._gateway.subscribe_to_key(*subscription_keys, scope=scope)

    async def unsubscribe_from_topic(self, *subscription_keys):
        await self._http.unsubscribe({"subscription_keys": list(subscription_keys)})

    async def subscribe_to_all(self, max_threads=50):
        """Subscribe to all lobbies, threads, and channels to receive message/reply events."""
        keys = []
        for lobby in self.lobbies:
            keys.append(lobby.subscription_key)

        thread_keys = []
        for channel in self.channels:
            keys.append(channel.subscription_key)
            for label in channel.labels:
                keys.append(label.subscription_key)

            stubs = await channel.fetch_thread_stubs(max_count=max_threads)

            for stub in stubs:
                thread_keys.append(stub.subscription_key)

        for thread in self.threads:
            keys.append(thread.subscription_key)

        await self.subscribe_to_topic(*keys)
        await self.subscribe_to_topic(*thread_keys, scope='content')

    async def subscribe_to_default(self):
        """Subscribe to the default set of topics, including the public SC community and all direct messages and
        group messages."""
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
        return super()._replace_lobby(payload)

    async def close(self):
        """End the run task and clean up resources."""
        self._gateway.close()
        await self._http.close()