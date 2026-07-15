from __future__ import annotations

import asyncio
import traceback
from typing import TYPE_CHECKING, Literal

from .gateway import Gateway
from .grpc_gateway import GRPCGateway
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
    def __init__(self, *, rsi_token: str = None, device_id: str = None,
                 transport: Literal['ws', 'grpc'] = 'ws', **kwargs):
        super().__init__(rsi_token=rsi_token, device_id=device_id, **kwargs)
        self._transport = transport
        if transport == 'grpc':
            self._gateway: Gateway | GRPCGateway = GRPCGateway(client=self, rsi_token=rsi_token, device_id=device_id)
        else:
            self._gateway: Gateway | GRPCGateway = Gateway(client=self, rsi_token=rsi_token, device_id=device_id)
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

    # ─── MESSAGE EVENTS ────────────────────────────────────────────────────────

    @register_callback('message.erase')
    async def _on_message_erase_raw(self, payload: dict):
        message_id = payload.get('message_id')
        lobby_id = payload.get('lobby_id')
        message = self.get_message(message_id) or Object(self, id=message_id)
        lobby = self.get_lobby(lobby_id) or Object(self, id=lobby_id) if lobby_id else None
        asyncio.ensure_future(self.on_message_erase(message, lobby))

    async def on_message_erase(self, message: Message | Object, lobby: Lobby | Object | None):
        """Called when a message is deleted."""
        pass

    # ─── LOBBY EVENTS ─────────────────────────────────────────────────────────

    @register_callback('message_lobby.new')
    async def _on_lobby_new_raw(self, payload: dict):
        lobby = self._replace_lobby(payload['message_lobby'])
        asyncio.ensure_future(self.on_lobby_new(lobby))

    async def on_lobby_new(self, lobby: Lobby):
        """Called when a new lobby is created."""
        pass

    @register_callback('message_lobby.update')
    async def _on_lobby_update_raw(self, payload: dict):
        lobby = self._replace_lobby(payload['message_lobby'])
        asyncio.ensure_future(self.on_lobby_update(lobby))

    async def on_lobby_update(self, lobby: Lobby):
        """Called when a lobby is edited (name, description, etc)."""
        pass

    @register_callback('message_lobby.erase')
    async def _on_lobby_erase_raw(self, payload: dict):
        lobby_id = payload.get('lobby_id')
        lobby = self._lobbies.pop(int(lobby_id), None) or Object(self, id=lobby_id)
        asyncio.ensure_future(self.on_lobby_erase(lobby))

    async def on_lobby_erase(self, lobby: Lobby | Object):
        """Called when a lobby is deleted."""
        pass

    @register_callback('message_lobby.leave')
    async def _on_lobby_leave_raw(self, payload: dict):
        member = self.get_member(payload.get('member_id')) or Object(self, id=payload.get('member_id'))
        lobby = self.get_lobby(payload.get('lobby_id')) or Object(self, id=payload.get('lobby_id'))
        asyncio.ensure_future(self.on_lobby_leave(lobby, member))

    async def on_lobby_leave(self, lobby: Lobby | Object, member: Member | Object):
        """Called when a member leaves a lobby."""
        pass

    @register_callback('message_lobby.kick')
    async def _on_lobby_kick_raw(self, payload: dict):
        member = self.get_member(payload.get('member_id')) or Object(self, id=payload.get('member_id'))
        lobby = self.get_lobby(payload.get('lobby_id')) or Object(self, id=payload.get('lobby_id'))
        asyncio.ensure_future(self.on_lobby_kick(lobby, member))

    async def on_lobby_kick(self, lobby: Lobby | Object, member: Member | Object):
        """Called when a member is kicked from a lobby."""
        pass

    @register_callback('message_lobby.latest.update')
    async def _on_lobby_latest_update_raw(self, payload: dict):
        lobby = self.get_lobby(payload.get('lobby_id')) or Object(self, id=payload.get('lobby_id'))
        message_id = payload.get('message_id')
        message = self.get_message(message_id) or Object(self, id=message_id) if message_id else None
        asyncio.ensure_future(self.on_lobby_latest_update(lobby, message))

    async def on_lobby_latest_update(self, lobby: Lobby | Object, message: Message | Object | None):
        """Called when the latest message marker is updated in a lobby."""
        pass

    # ─── FORUM EVENTS ─────────────────────────────────────────────────────────

    @register_callback('forum.thread.edit')
    async def _on_forum_thread_edit_raw(self, payload: dict):
        thread_id = payload.get('thread_id')
        thread = self.get_thread(thread_id) or self.get_thread_stub(thread_id) or Object(self, id=thread_id)
        asyncio.ensure_future(self.on_forum_thread_edit(thread, payload))

    async def on_forum_thread_edit(self, thread: Thread | ThreadStub | Object, payload: dict):
        """Called when a thread is edited."""
        pass

    @register_callback('forum.thread.reply.edit')
    async def _on_forum_thread_reply_edit_raw(self, payload: dict):
        reply_id = payload.get('reply_id')
        thread_id = payload.get('thread_id')
        reply = self.get_reply(reply_id) or Object(self, id=reply_id)
        thread = self.get_thread(thread_id) or self.get_thread_stub(thread_id) or Object(self, id=thread_id)
        asyncio.ensure_future(self.on_forum_thread_reply_edit(thread, reply, payload))

    async def on_forum_thread_reply_edit(self, thread: Thread | ThreadStub | Object, reply: Reply | Object, payload: dict):
        """Called when a reply is edited."""
        pass

    @register_callback('forum_thread.erase')
    async def _on_forum_thread_erase_raw(self, payload: dict):
        thread_id = payload.get('thread_id') or payload.get('forum_thread_id')
        thread = self._threads.pop(int(thread_id), None) if thread_id else None
        if not thread:
            thread = self._thread_stubs.pop(int(thread_id), None) if thread_id else None
        if not thread:
            thread = Object(self, id=thread_id)
        asyncio.ensure_future(self.on_forum_thread_erase(thread))

    async def on_forum_thread_erase(self, thread: Thread | ThreadStub | Object):
        """Called when a thread is erased."""
        pass

    @register_callback('forum_channel_group.new')
    async def _on_forum_channel_group_new_raw(self, payload: dict):
        asyncio.ensure_future(self.on_forum_channel_group_new(payload))

    async def on_forum_channel_group_new(self, payload: dict):
        """Called when a new forum channel group is created."""
        pass

    @register_callback('forum_channel_group.update')
    async def _on_forum_channel_group_update_raw(self, payload: dict):
        asyncio.ensure_future(self.on_forum_channel_group_update(payload))

    async def on_forum_channel_group_update(self, payload: dict):
        """Called when a forum channel group is updated."""
        pass

    @register_callback('forum_channel_group.remove')
    async def _on_forum_channel_group_remove_raw(self, payload: dict):
        asyncio.ensure_future(self.on_forum_channel_group_remove(payload))

    async def on_forum_channel_group_remove(self, payload: dict):
        """Called when a forum channel group is removed."""
        pass

    @register_callback('forum_label.new')
    async def _on_forum_label_new_raw(self, payload: dict):
        asyncio.ensure_future(self.on_forum_label_new(payload))

    async def on_forum_label_new(self, payload: dict):
        """Called when a new forum label is created."""
        pass

    @register_callback('forum_label.edit')
    async def _on_forum_label_edit_raw(self, payload: dict):
        asyncio.ensure_future(self.on_forum_label_edit(payload))

    async def on_forum_label_edit(self, payload: dict):
        """Called when a forum label is edited."""
        pass

    @register_callback('forum_label.remove')
    async def _on_forum_label_remove_raw(self, payload: dict):
        asyncio.ensure_future(self.on_forum_label_remove(payload))

    async def on_forum_label_remove(self, payload: dict):
        """Called when a forum label is removed."""
        pass

    @register_callback('forum.thread.marker.update')
    async def _on_forum_thread_marker_update_raw(self, payload: dict):
        thread_id = payload.get('thread_id')
        thread = self.get_thread(thread_id) or self.get_thread_stub(thread_id) or Object(self, id=thread_id)
        asyncio.ensure_future(self.on_forum_thread_marker_update(thread, payload))

    async def on_forum_thread_marker_update(self, thread: Thread | ThreadStub | Object, payload: dict):
        """Called when a thread marker is updated."""
        pass

    @register_callback('forum.thread.replies_count.update')
    async def _on_forum_thread_replies_count_update_raw(self, payload: dict):
        thread_id = payload.get('thread_id')
        thread = self.get_thread(thread_id) or self.get_thread_stub(thread_id) or Object(self, id=thread_id)
        count = payload.get('replies_count')
        asyncio.ensure_future(self.on_forum_thread_replies_count_update(thread, count))

    async def on_forum_thread_replies_count_update(self, thread: Thread | ThreadStub | Object, count: int | None):
        """Called when a thread's reply count changes."""
        pass

    @register_callback('forum.label.read')
    async def _on_forum_label_read_raw(self, payload: dict):
        asyncio.ensure_future(self.on_forum_label_read(payload))

    async def on_forum_label_read(self, payload: dict):
        """Called when a forum label read marker is set."""
        pass

    @register_callback('forum.label.read.update')
    async def _on_forum_label_read_update_raw(self, payload: dict):
        asyncio.ensure_future(self.on_forum_label_read_update(payload))

    async def on_forum_label_read_update(self, payload: dict):
        """Called when a forum label read marker is updated."""
        pass

    # ─── BOOKMARK EVENTS ──────────────────────────────────────────────────────

    @register_callback('bookmark.add')
    async def _on_bookmark_add_raw(self, payload: dict):
        asyncio.ensure_future(self.on_bookmark_add(payload))

    async def on_bookmark_add(self, payload: dict):
        """Called when a bookmark is added."""
        pass

    @register_callback('bookmark.remove')
    async def _on_bookmark_remove_raw(self, payload: dict):
        asyncio.ensure_future(self.on_bookmark_remove(payload))

    async def on_bookmark_remove(self, payload: dict):
        """Called when a bookmark is removed."""
        pass

    @register_callback('bookmark.move')
    async def _on_bookmark_move_raw(self, payload: dict):
        asyncio.ensure_future(self.on_bookmark_move(payload))

    async def on_bookmark_move(self, payload: dict):
        """Called when a bookmark is moved."""
        pass

    @register_callback('bookmark.rename')
    async def _on_bookmark_rename_raw(self, payload: dict):
        asyncio.ensure_future(self.on_bookmark_rename(payload))

    async def on_bookmark_rename(self, payload: dict):
        """Called when a bookmark is renamed."""
        pass

    # ─── EMOJI EVENTS ─────────────────────────────────────────────────────────

    @register_callback('emoji.new')
    async def _on_emoji_new_raw(self, payload: dict):
        asyncio.ensure_future(self.on_emoji_new(payload))

    async def on_emoji_new(self, payload: dict):
        """Called when an emoji is created."""
        pass

    @register_callback('emoji.remove')
    async def _on_emoji_remove_raw(self, payload: dict):
        asyncio.ensure_future(self.on_emoji_remove(payload))

    async def on_emoji_remove(self, payload: dict):
        """Called when an emoji is removed."""
        pass

    @register_callback('custom_emoji.create')
    async def _on_custom_emoji_create_raw(self, payload: dict):
        asyncio.ensure_future(self.on_custom_emoji_create(payload))

    async def on_custom_emoji_create(self, payload: dict):
        """Called when a custom emoji is created."""
        pass

    @register_callback('custom_emoji.remove')
    async def _on_custom_emoji_remove_raw(self, payload: dict):
        asyncio.ensure_future(self.on_custom_emoji_remove(payload))

    async def on_custom_emoji_remove(self, payload: dict):
        """Called when a custom emoji is removed."""
        pass

    # ─── FRIEND EVENTS ────────────────────────────────────────────────────────

    @register_callback('friend_request.new')
    async def _on_friend_request_new_raw(self, payload: dict):
        member_id = payload.get('member_id')
        member = self.get_member(member_id) or Object(self, id=member_id)
        asyncio.ensure_future(self.on_friend_request_new(member, payload))

    async def on_friend_request_new(self, member: Member | Object, payload: dict):
        """Called when a new friend request is received."""
        pass

    @register_callback('friend_request.accept')
    async def _on_friend_request_accept_raw(self, payload: dict):
        member_id = payload.get('member_id')
        member = self.get_member(member_id) or Object(self, id=member_id)
        asyncio.ensure_future(self.on_friend_request_accept(member, payload))

    async def on_friend_request_accept(self, member: Member | Object, payload: dict):
        """Called when a friend request is accepted."""
        pass

    @register_callback('friend_request.decline')
    async def _on_friend_request_decline_raw(self, payload: dict):
        member_id = payload.get('member_id')
        member = self.get_member(member_id) or Object(self, id=member_id)
        asyncio.ensure_future(self.on_friend_request_decline(member, payload))

    async def on_friend_request_decline(self, member: Member | Object, payload: dict):
        """Called when a friend request is declined."""
        pass

    @register_callback('friend_request.cancel')
    async def _on_friend_request_cancel_raw(self, payload: dict):
        member_id = payload.get('member_id')
        member = self.get_member(member_id) or Object(self, id=member_id)
        asyncio.ensure_future(self.on_friend_request_cancel(member, payload))

    async def on_friend_request_cancel(self, member: Member | Object, payload: dict):
        """Called when a friend request is cancelled."""
        pass

    @register_callback('friendship.new')
    async def _on_friendship_new_raw(self, payload: dict):
        member_id = payload.get('member_id')
        member = self.get_member(member_id) or Object(self, id=member_id)
        asyncio.ensure_future(self.on_friendship_new(member, payload))

    async def on_friendship_new(self, member: Member | Object, payload: dict):
        """Called when a new friendship is established."""
        pass

    @register_callback('friendship.remove')
    async def _on_friendship_remove_raw(self, payload: dict):
        member_id = payload.get('member_id')
        member = self.get_member(member_id) or Object(self, id=member_id)
        asyncio.ensure_future(self.on_friendship_remove(member, payload))

    async def on_friendship_remove(self, member: Member | Object, payload: dict):
        """Called when a friendship is removed."""
        pass

    # ─── GUIDE SYSTEM EVENTS ──────────────────────────────────────────────────

    @register_callback('guide_request.new')
    async def _on_guide_request_new_raw(self, payload: dict):
        asyncio.ensure_future(self.on_guide_request_new(payload))

    async def on_guide_request_new(self, payload: dict):
        """Called when a new guide request is received."""
        pass

    @register_callback('guide_request.accept')
    async def _on_guide_request_accept_raw(self, payload: dict):
        asyncio.ensure_future(self.on_guide_request_accept(payload))

    async def on_guide_request_accept(self, payload: dict):
        """Called when a guide request is accepted."""
        pass

    @register_callback('guide_request.decline')
    async def _on_guide_request_decline_raw(self, payload: dict):
        asyncio.ensure_future(self.on_guide_request_decline(payload))

    async def on_guide_request_decline(self, payload: dict):
        """Called when a guide request is declined."""
        pass

    @register_callback('guide_request.cancel')
    async def _on_guide_request_cancel_raw(self, payload: dict):
        asyncio.ensure_future(self.on_guide_request_cancel(payload))

    async def on_guide_request_cancel(self, payload: dict):
        """Called when a guide request is cancelled."""
        pass

    @register_callback('guide_request.remove')
    async def _on_guide_request_remove_raw(self, payload: dict):
        asyncio.ensure_future(self.on_guide_request_remove(payload))

    async def on_guide_request_remove(self, payload: dict):
        """Called when a guide request is removed."""
        pass

    @register_callback('guide_request.remove_all')
    async def _on_guide_request_remove_all_raw(self, payload: dict):
        asyncio.ensure_future(self.on_guide_request_remove_all(payload))

    async def on_guide_request_remove_all(self, payload: dict):
        """Called when all guide requests are removed."""
        pass

    @register_callback('guide_request.timeout')
    async def _on_guide_request_timeout_raw(self, payload: dict):
        asyncio.ensure_future(self.on_guide_request_timeout(payload))

    async def on_guide_request_timeout(self, payload: dict):
        """Called when a guide request times out."""
        pass

    @register_callback('guide_session.create')
    async def _on_guide_session_create_raw(self, payload: dict):
        asyncio.ensure_future(self.on_guide_session_create(payload))

    async def on_guide_session_create(self, payload: dict):
        """Called when a guide session starts."""
        pass

    @register_callback('guide_session.endorse')
    async def _on_guide_session_endorse_raw(self, payload: dict):
        asyncio.ensure_future(self.on_guide_session_endorse(payload))

    async def on_guide_session_endorse(self, payload: dict):
        """Called when a guide is endorsed."""
        pass

    @register_callback('guide_session.terminate')
    async def _on_guide_session_terminate_raw(self, payload: dict):
        asyncio.ensure_future(self.on_guide_session_terminate(payload))

    async def on_guide_session_terminate(self, payload: dict):
        """Called when a guide session ends."""
        pass

    # ─── INVITE EVENTS ────────────────────────────────────────────────────────

    @register_callback('invite.new')
    async def _on_invite_new_raw(self, payload: dict):
        asyncio.ensure_future(self.on_invite_new(payload))

    async def on_invite_new(self, payload: dict):
        """Called when a lobby invite is received."""
        pass

    @register_callback('invite.accept')
    async def _on_invite_accept_raw(self, payload: dict):
        asyncio.ensure_future(self.on_invite_accept(payload))

    async def on_invite_accept(self, payload: dict):
        """Called when an invite is accepted."""
        pass

    @register_callback('invite.cancel')
    async def _on_invite_cancel_raw(self, payload: dict):
        asyncio.ensure_future(self.on_invite_cancel(payload))

    async def on_invite_cancel(self, payload: dict):
        """Called when an invite is cancelled."""
        pass

    @register_callback('invite.decline')
    async def _on_invite_decline_raw(self, payload: dict):
        asyncio.ensure_future(self.on_invite_decline(payload))

    async def on_invite_decline(self, payload: dict):
        """Called when an invite is declined."""
        pass

    # ─── NOTIFICATION EVENTS ──────────────────────────────────────────────────

    @register_callback('notification.new')
    async def _on_notification_new_raw(self, payload: dict):
        asyncio.ensure_future(self.on_notification_new(payload))

    async def on_notification_new(self, payload: dict):
        """Called when a new notification is received."""
        pass

    @register_callback('notification.read')
    async def _on_notification_read_raw(self, payload: dict):
        asyncio.ensure_future(self.on_notification_read(payload))

    async def on_notification_read(self, payload: dict):
        """Called when a notification is marked read."""
        pass

    @register_callback('notification.remove')
    async def _on_notification_remove_raw(self, payload: dict):
        asyncio.ensure_future(self.on_notification_remove(payload))

    async def on_notification_remove(self, payload: dict):
        """Called when a notification is removed."""
        pass

    @register_callback('notification.read_all')
    async def _on_notification_read_all_raw(self, payload: dict):
        asyncio.ensure_future(self.on_notification_read_all(payload))

    async def on_notification_read_all(self, payload: dict):
        """Called when all notifications are marked read."""
        pass

    @register_callback('notification.remove_all')
    async def _on_notification_remove_all_raw(self, payload: dict):
        asyncio.ensure_future(self.on_notification_remove_all(payload))

    async def on_notification_remove_all(self, payload: dict):
        """Called when all notifications are removed."""
        pass

    @register_callback('notification.update')
    async def _on_notification_update_raw(self, payload: dict):
        asyncio.ensure_future(self.on_notification_update(payload))

    async def on_notification_update(self, payload: dict):
        """Called when a notification is updated."""
        pass

    # ─── ROLE EVENTS ──────────────────────────────────────────────────────────

    @register_callback('role.new')
    async def _on_role_new_raw(self, payload: dict):
        community_id = payload.get('community_id')
        community = self.get_community(community_id)
        role = None
        if community and payload.get('role'):
            role = community._replace_role(payload['role'])
        asyncio.ensure_future(self.on_role_new(community, role, payload))

    async def on_role_new(self, community: Community | None, role: Role | None, payload: dict):
        """Called when a role is created."""
        pass

    @register_callback('role.update')
    async def _on_role_update_raw(self, payload: dict):
        community_id = payload.get('community_id')
        community = self.get_community(community_id)
        role = None
        if community and payload.get('role'):
            role = community._replace_role(payload['role'])
        asyncio.ensure_future(self.on_role_update(community, role, payload))

    async def on_role_update(self, community: Community | None, role: Role | None, payload: dict):
        """Called when a role is edited."""
        pass

    @register_callback('role.move')
    async def _on_role_move_raw(self, payload: dict):
        asyncio.ensure_future(self.on_role_move(payload))

    async def on_role_move(self, payload: dict):
        """Called when a role is moved (deprecated, use role.reorder)."""
        pass

    @register_callback('role.remove')
    async def _on_role_remove_raw(self, payload: dict):
        community_id = payload.get('community_id')
        community = self.get_community(community_id)
        role_id = payload.get('role_id')
        role = None
        if community and role_id:
            role = community._roles.pop(int(role_id), None)
        asyncio.ensure_future(self.on_role_remove(community, role, payload))

    async def on_role_remove(self, community: Community | None, role: Role | None, payload: dict):
        """Called when a role is deleted."""
        pass

    @register_callback('role.reorder')
    async def _on_role_reorder_raw(self, payload: dict):
        asyncio.ensure_future(self.on_role_reorder(payload))

    async def on_role_reorder(self, payload: dict):
        """Called when roles are reordered."""
        pass

    # ─── OTHER EVENTS ─────────────────────────────────────────────────────────

    @register_callback('community.update')
    async def _on_community_update_raw(self, payload: dict):
        community = None
        if payload.get('community'):
            community = self._replace_community(payload['community'])
        asyncio.ensure_future(self.on_community_update(community, payload))

    async def on_community_update(self, community: Community | None, payload: dict):
        """Called when community settings change."""
        pass

    @register_callback('private_lobbies.update')
    async def _on_private_lobbies_update_raw(self, payload: dict):
        asyncio.ensure_future(self.on_private_lobbies_update(payload))

    async def on_private_lobbies_update(self, payload: dict):
        """Called when the DM list changes."""
        pass

    @register_callback('settings.update')
    async def _on_settings_update_raw(self, payload: dict):
        asyncio.ensure_future(self.on_settings_update(payload))

    async def on_settings_update(self, payload: dict):
        """Called when user settings change."""
        pass

    @register_callback('server.stop')
    async def _on_server_stop_raw(self, payload: dict):
        asyncio.ensure_future(self.on_server_stop(payload))

    async def on_server_stop(self, payload: dict):
        """Called when the server is shutting down."""
        pass

    @register_callback('vote.add')
    async def _on_vote_add_raw(self, payload: dict):
        asyncio.ensure_future(self.on_vote_add(payload))

    async def on_vote_add(self, payload: dict):
        """Called when a vote is added to a thread or reply."""
        pass

    @register_callback('vote.remove')
    async def _on_vote_remove_raw(self, payload: dict):
        asyncio.ensure_future(self.on_vote_remove(payload))

    async def on_vote_remove(self, payload: dict):
        """Called when a vote is removed from a thread or reply."""
        pass

    # ─── UNHANDLED ────────────────────────────────────────────────────────────

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

    async def send_typing(self, lobby: Lobby | int, *, start: bool = True):
        """Send a typing indicator to a lobby via WebSocket.

        Parameters
        ----------
        lobby : Lobby | int
            The lobby (or lobby ID) to send the typing event to.
        start : bool
            If True, sends typing start; if False, sends typing end.
        """
        lobby_id = lobby.id if isinstance(lobby, Lobby) else int(lobby)
        event_type = 'message_lobby.typing.start' if start else 'message_lobby.typing.end'
        await self._gateway.send_event(event_type, {"lobby_id": lobby_id})

    async def close(self):
        """End the run task and clean up resources."""
        self._gateway.close()
        await self._http.close()