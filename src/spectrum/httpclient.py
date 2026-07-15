from __future__ import annotations

import asyncio
import logging
import sys
import traceback
from collections.abc import AsyncIterator
from typing import Optional

from .errors import NullResponseError, ResourceNotFound
from .http import HTTP
from .models import Lobby, Member, Community, Message, Forum, channel, Thread, Reply, Role
from .models.thread import ThreadStub
from .models.upload import Upload
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
        self._channels: dict[int, channel.Channel] = {}
        self._threads: dict[int, Thread] = {}
        self._thread_stubs: dict[int, ThreadStub] = {}
        self._replies: dict[int, Reply] = {}
        self.log_handler = log_handler
        self.me: Optional[Member] = None

    async def close(self):
        await self._http.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

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
        try:
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
        except Exception as e:
            logging.error("Error occurred replacing lobby: %s\nFailing Payload: %s",
                          traceback.format_exception_only(e),
                          payload)
            raise e

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

    def get_channel(self, channel_id: str | int) -> Optional[channel.Channel]:
        return self._channels.get(int(channel_id))

    @property
    def channels(self) -> list[channel.Channel]:
        return list(self._channels.values())

    def _replace_channel(self, payload: dict):
        c = self.get_channel(payload['id'])
        if c:
            c.__init__(self, payload)
        else:
            self._channels[int(payload['id'])] = c = channel.Channel(self, payload)

        return c

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

    def get_thread_stub(self, thread_id: str | int) -> Optional[ThreadStub]:
        return self._thread_stubs.get(int(thread_id))

    @property
    def thread_stubs(self) -> list[ThreadStub]:
        return list(self._thread_stubs.values())

    def _replace_thread_stub(self, payload: dict):
        self._thread_stubs[int(payload['id'])] = thread = ThreadStub(**payload)
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

    async def fetch_lobby(self, lobby_id: int | str) -> Lobby:
        payload = await self._http.fetch_lobby_info(dict(lobby_id=lobby_id))
        return self._replace_lobby(payload)

    async def fetch_member_by_id(self, member_id: int | str) -> Member:
        try:
            payload = await self._http.fetch_member_by_id(dict(member_id=member_id))
            return self._replace_member(payload['member'])
        except NullResponseError:
            raise ResourceNotFound("Member not found")

    async def fetch_member_by_handle(self, handle: str) -> Member:
        payload = await self._http.fetch_member_by_handle(dict(nickname=handle))
        return self._replace_member(payload['member'])

    async def search_users(self, query: str, ignore_self: bool = True,
                           community: Community | None = None, max_count: int | None = None,
                           page_delay: float = 1.0) -> AsyncIterator[Member]:
        page = 1
        count = 0
        while True:
            payload = await self._http.search_users({
                "community_id": community.id if community else None,
                "text": query,
                "ignore_self": ignore_self,
                "pagesize": 15,
                "page": page,
            })

            for member in payload['members']:
                yield self._replace_member(member)
                count += 1

                if max_count and count >= max_count:
                    return

            if payload['page'] >= payload['pages_total']:
                return

            page = payload['page'] + 1
            if page_delay:
                await asyncio.sleep(page_delay)

    async def set_status(self, status: str, info: str | None = None) -> None:
        await self._http.set_status({"status": status, "info": info})

    async def add_friend(self, member_id: int | str) -> None:
        await self._http.add_friend({"member_id": str(member_id)})

    async def remove_friend(self, member_id: int | str) -> None:
        await self._http.remove_friend({"member_id": str(member_id)})

    async def block_member(self, member_id: int | str) -> None:
        await self._http.blocklist_add({"member_id": str(member_id)})

    async def unblock_member(self, member_id: int | str) -> None:
        await self._http.blocklist_remove({"member_id": str(member_id)})

    async def search_content(self, text: str = "", community_id: int | str = "1",
                             content_types: list[str] | None = None, page: int = 1,
                             sort: str = "latest", range: str = "year",
                             author: str | None = None, visibility: str = "nonerased") -> list[dict]:
        payload = {
            "community_id": str(community_id),
            "type": content_types or ["op", "reply", "chat"],
            "text": text,
            "page": page,
            "sort": sort,
            "range": range,
            "visibility": visibility,
        }
        if author:
            payload["author"] = str(author)
        resp = await self._http.extended_search(payload)
        return resp['hits']['hits']

    # ── Bookmarks ──

    async def bookmark_move(self, bookmark_id: int | str, target_folder_id: int | str, position: int = 0) -> dict:
        """Move a bookmark to a different folder."""
        return await self._http.bookmark_move({
            "bookmark_id": str(bookmark_id),
            "target_folder_id": str(target_folder_id),
            "position": position,
        })

    async def bookmark_remove(self, bookmark_id: int | str) -> dict:
        """Remove a bookmark."""
        return await self._http.bookmark_remove({"bookmark_id": str(bookmark_id)})

    async def bookmark_rename(self, bookmark_id: int | str, name: str) -> dict:
        """Rename a bookmark."""
        return await self._http.bookmark_rename({"bookmark_id": str(bookmark_id), "name": name})

    async def bookmarks_list(self, community_id: int | str = "1") -> dict:
        """List all bookmarks for a community."""
        return await self._http.bookmarks_list({"community_id": str(community_id)})

    # ── Broadcast Messages ──

    async def broadcast_message_create(self, community_id: int | str, content_blocks: list, plaintext: str) -> dict:
        """Create a broadcast message."""
        return await self._http.broadcast_message_create({
            "community_id": str(community_id),
            "content_blocks": content_blocks,
            "plaintext": plaintext,
        })

    async def broadcast_message_edit(self, broadcast_message_id: int | str, content_blocks: list, plaintext: str) -> dict:
        """Edit a broadcast message."""
        return await self._http.broadcast_message_edit({
            "broadcast_message_id": str(broadcast_message_id),
            "content_blocks": content_blocks,
            "plaintext": plaintext,
        })

    async def broadcast_message_list(self, community_id: int | str = "1") -> dict:
        """List broadcast messages for a community."""
        return await self._http.make_request("/api/spectrum/broadcast-message/list", {
            "community_id": str(community_id),
        })

    async def broadcast_message_remove(self, broadcast_message_id: int | str) -> dict:
        """Remove a broadcast message."""
        return await self._http.broadcast_message_remove({
            "broadcast_message_id": str(broadcast_message_id),
        })

    # ── Emoji ──

    async def emoji_create(self, community_id: int | str, name: str, media_id: int | str) -> dict:
        """Create a custom emoji from an uploaded media."""
        return await self._http.emoji_create({
            "community_id": str(community_id),
            "name": name,
            "media_id": str(media_id),
        })

    async def emoji_erase(self, community_id: int | str, emoji_id: int | str) -> dict:
        """Delete a custom emoji."""
        return await self._http.emoji_erase({
            "community_id": str(community_id),
            "emoji_id": str(emoji_id),
        })

    async def upload_emoji(self, file_path: str, filename: str | None = None, content_type: str | None = None) -> Upload:
        """Upload an emoji image. Returns an Upload object with media data."""
        data = await self._http.upload_emoji(file_path, filename=filename, content_type=content_type)
        return Upload(data)

    # ── Flag / Report ──

    async def flag_content(self, entity_type: str, entity_id: int | str, reason: str, comment: str = "") -> dict:
        """Report/flag content for moderation."""
        return await self._http.flag_content({
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "reason": reason,
            "comment": comment,
        })

    # ── Forum Channel CRUD ──

    async def erase_category(self, channel_id: int | str) -> dict:
        """Delete a forum channel/category."""
        return await self._http.erase_category({"channel_id": str(channel_id)})

    async def erase_categories_group(self, group_id: int | str) -> dict:
        """Delete a forum channel group."""
        return await self._http.erase_categories_group({"group_id": str(group_id)})

    async def move_categories_group(self, community_id: int | str, source_group_id: int | str, target_group_id: int | str) -> dict:
        """Move a forum channel group to a new position."""
        return await self._http.move_categories_group({
            "community_id": str(community_id),
            "source_group_id": str(source_group_id),
            "target_group_id": str(target_group_id),
        })

    async def move_category(self, channel_id: int | str, target_group_id: int | str, position: int = 0) -> dict:
        """Move a forum channel to a different group."""
        return await self._http.move_category({
            "channel_id": str(channel_id),
            "target_group_id": str(target_group_id),
            "position": position,
        })

    # ── Forum Thread Bulk Ops ──

    async def edit_threads(self, *threads, label_id: int | str | None = None, channel_id: int | str | None = None) -> dict:
        """Bulk edit threads (move to channel, change label)."""
        payload = {"thread_ids": [str(t.id) if hasattr(t, 'id') else str(t) for t in threads]}
        if label_id is not None:
            payload["label_id"] = str(label_id)
        if channel_id is not None:
            payload["channel_id"] = str(channel_id)
        return await self._http.edit_threads(payload)

    async def unlock_threads(self, *threads) -> dict:
        """Bulk unlock threads."""
        return await self._http.unlock_threads({
            "thread_ids": [str(t.id) if hasattr(t, 'id') else str(t) for t in threads]
        })

    async def unpin_threads(self, *threads) -> dict:
        """Bulk unpin threads."""
        return await self._http.unpin_threads({
            "thread_ids": [str(t.id) if hasattr(t, 'id') else str(t) for t in threads]
        })

    async def unsink_threads(self, *threads) -> dict:
        """Bulk unsink threads."""
        return await self._http.unsink_threads({
            "thread_ids": [str(t.id) if hasattr(t, 'id') else str(t) for t in threads]
        })

    # ── Forum Thread Single Ops ──

    async def edit_thread(self, thread_id: int | str, subject: str | None = None,
                          content_blocks: list | None = None, plaintext: str | None = None,
                          label_id: int | str | None = None, is_locked: bool = False,
                          is_reply_nesting_disabled: bool = False) -> dict:
        """Edit a single thread's subject, body, or properties."""
        payload = {"thread_id": str(thread_id), "is_locked": is_locked, "is_reply_nesting_disabled": is_reply_nesting_disabled}
        if subject is not None:
            payload["subject"] = subject
        if content_blocks is not None:
            payload["content_blocks"] = content_blocks
        if plaintext is not None:
            payload["plaintext"] = plaintext
        if label_id is not None:
            payload["label_id"] = str(label_id)
        return await self._http.edit_thread(payload)

    async def erase_thread(self, thread_id: int | str, reason: str | None = None) -> dict:
        """Erase (delete) a single thread."""
        payload = {"thread_id": str(thread_id)}
        if reason:
            payload["reason"] = reason
        return await self._http.erase_thread(payload)

    # ── Forum Replies ──

    async def fetch_thread_replies(self, thread_id: int | str, page: int = 1, sort: str = "oldest") -> dict:
        """Fetch paginated replies for a thread."""
        return await self._http.fetch_thread_replies({
            "thread_id": str(thread_id),
            "page": page,
            "sort": sort,
        })

    async def fetch_thread_reply(self, reply_id: int | str) -> dict:
        """Fetch a single reply by ID."""
        return await self._http.fetch_thread_reply({"reply_id": str(reply_id)})

    async def fetch_reply_children(self, reply_id: int | str, page: int = 1, sort: str = "oldest") -> dict:
        """Fetch child replies (nested replies) of a reply."""
        return await self._http.fetch_reply_children({
            "reply_id": str(reply_id),
            "page": page,
            "sort": sort,
        })

    async def edit_reply(self, reply_id: int | str, content_blocks: list, plaintext: str) -> dict:
        """Edit a forum thread reply."""
        return await self._http.edit_reply({
            "reply_id": str(reply_id),
            "content_blocks": content_blocks,
            "plaintext": plaintext,
        })

    async def erase_reply(self, reply_id: int | str, reason: str | None = None) -> dict:
        """Erase (delete) a forum thread reply."""
        payload = {"reply_id": str(reply_id)}
        if reason:
            payload["reason"] = reason
        return await self._http.erase_reply(payload)

    # ── Friends (expanded) ──

    async def friend_request_accept(self, member_id: int | str) -> dict:
        """Accept a friend request."""
        return await self._http.friend_request_accept({"member_id": str(member_id)})

    async def friend_request_cancel(self, member_id: int | str) -> dict:
        """Cancel a pending friend request."""
        return await self._http.friend_request_cancel({"member_id": str(member_id)})

    async def friend_request_create(self, member_id: int | str) -> dict:
        """Send a friend request."""
        return await self._http.friend_request_create({"member_id": str(member_id)})

    async def friend_request_decline(self, member_id: int | str) -> dict:
        """Decline a friend request."""
        return await self._http.friend_request_decline({"member_id": str(member_id)})

    async def friend_request_list(self) -> dict:
        """List pending friend requests."""
        return await self._http.friend_request_list({})

    async def friend_list(self) -> dict:
        """List all friends."""
        return await self._http.friend_list({})

    async def friend_search(self, text: str) -> dict:
        """Search within friends list."""
        return await self._http.friend_search({"text": text})

    # ── Guide System ──

    async def guide_deregister(self, community_id: int | str = "1") -> dict:
        """Deregister as a guide."""
        return await self._http.guide_deregister({"community_id": str(community_id)})

    async def guide_endorsement_create(self, guide_id: int | str, comment: str = "") -> dict:
        """Endorse a guide."""
        return await self._http.guide_endorsement_create({
            "guide_id": str(guide_id),
            "comment": comment,
        })

    async def guide_endorsement_decline(self, endorsement_id: int | str) -> dict:
        """Decline a guide endorsement."""
        return await self._http.guide_endorsement_decline({"endorsement_id": str(endorsement_id)})

    async def guide_profile_update(self, community_id: int | str, bio: str, topics: list[str] | None = None) -> dict:
        """Update guide profile."""
        payload = {"community_id": str(community_id), "bio": bio}
        if topics is not None:
            payload["topics"] = topics
        return await self._http.guide_profile_update(payload)

    async def guide_register(self, community_id: int | str, topics: list[str], bio: str = "") -> dict:
        """Register as a guide."""
        return await self._http.guide_register({
            "community_id": str(community_id),
            "topics": topics,
            "bio": bio,
        })

    async def guide_registration_criteria(self, community_id: int | str = "1") -> dict:
        """Get guide registration criteria."""
        return await self._http.guide_registration_criteria({"community_id": str(community_id)})

    async def guide_request_accept(self, request_id: int | str) -> dict:
        """Accept a guide request."""
        return await self._http.guide_request_accept({"request_id": str(request_id)})

    async def guide_request_cancel(self, request_id: int | str) -> dict:
        """Cancel a guide request."""
        return await self._http.guide_request_cancel({"request_id": str(request_id)})

    async def guide_request_create(self, community_id: int | str, topic: str, message: str = "") -> dict:
        """Create a guide request."""
        return await self._http.guide_request_create({
            "community_id": str(community_id),
            "topic": topic,
            "message": message,
        })

    async def guide_request_decline(self, request_id: int | str) -> dict:
        """Decline a guide request."""
        return await self._http.guide_request_decline({"request_id": str(request_id)})

    async def guide_request_remove(self, request_id: int | str) -> dict:
        """Remove a guide request."""
        return await self._http.guide_request_remove({"request_id": str(request_id)})

    async def guide_request_remove_all(self, community_id: int | str = "1") -> dict:
        """Remove all guide requests."""
        return await self._http.guide_request_remove_all({"community_id": str(community_id)})

    async def guide_search(self, community_id: int | str = "1", topic: str | None = None, page: int = 1) -> dict:
        """Search for guides."""
        payload = {"community_id": str(community_id), "page": page}
        if topic:
            payload["topic"] = topic
        return await self._http.guide_search(payload)

    async def guide_session_terminate(self, session_id: int | str) -> dict:
        """Terminate a guide session."""
        return await self._http.guide_session_terminate({"session_id": str(session_id)})

    async def guide_topics_list(self, community_id: int | str = "1") -> dict:
        """List available guide topics."""
        return await self._http.guide_topics_list({"community_id": str(community_id)})

    # ── Lobby (expanded) ──

    async def lobby_accept_invite(self, lobby_id: int | str) -> dict:
        """Accept a lobby invite."""
        return await self._http.lobby_accept_invite({"lobby_id": str(lobby_id)})

    async def lobby_cancel_invite(self, lobby_id: int | str, member_id: int | str) -> dict:
        """Cancel a lobby invite."""
        return await self._http.lobby_cancel_invite({
            "lobby_id": str(lobby_id),
            "member_id": str(member_id),
        })

    async def lobby_close_private(self, lobby_id: int | str) -> dict:
        """Close a private lobby."""
        return await self._http.lobby_close_private({"lobby_id": str(lobby_id)})

    async def lobby_decline_invite(self, lobby_id: int | str) -> dict:
        """Decline a lobby invite."""
        return await self._http.lobby_decline_invite({"lobby_id": str(lobby_id)})

    async def lobby_erase(self, lobby_id: int | str) -> dict:
        """Delete a lobby."""
        return await self._http.lobby_erase({"lobby_id": str(lobby_id)})

    async def lobby_guide_session_history(self, lobby_id: int | str) -> dict:
        """Get guide session history for a lobby."""
        return await self._http.lobby_guide_session_history({"lobby_id": str(lobby_id)})

    async def lobby_invite(self, lobby_id: int | str, member_id: int | str) -> dict:
        """Invite a member to a lobby."""
        return await self._http.lobby_invite({
            "lobby_id": str(lobby_id),
            "member_id": str(member_id),
        })

    async def lobby_kick(self, lobby_id: int | str, member_id: int | str) -> dict:
        """Kick a member from a lobby."""
        return await self._http.lobby_kick({
            "lobby_id": str(lobby_id),
            "member_id": str(member_id),
        })

    async def lobby_leave(self, lobby_id: int | str) -> dict:
        """Leave a lobby."""
        return await self._http.lobby_leave({"lobby_id": str(lobby_id)})

    async def lobby_list_invites(self, lobby_id: int | str) -> dict:
        """List pending invites for a lobby."""
        return await self._http.lobby_list_invites({"lobby_id": str(lobby_id)})

    async def lobby_move(self, lobby_id: int | str, target_group_id: int | str, position: int = 0) -> dict:
        """Move a lobby to a different group."""
        return await self._http.lobby_move({
            "lobby_id": str(lobby_id),
            "target_group_id": str(target_group_id),
            "position": position,
        })

    async def lobby_transfer_leadership(self, lobby_id: int | str, member_id: int | str) -> dict:
        """Transfer lobby leadership to another member."""
        return await self._http.lobby_transfer_leadership({
            "lobby_id": str(lobby_id),
            "member_id": str(member_id),
        })

    # ── Member (expanded) ──

    async def fetch_member_spoken_languages(self, member_id: int | str) -> dict:
        """Fetch spoken languages for a member."""
        return await self._http.member_spoken_languages({"member_id": str(member_id)})

    # ── Message (expanded) ──

    async def message_erase(self, message_id: int | str) -> dict:
        """Hard-delete a message (permanent)."""
        return await self._http.message_erase({"message_id": str(message_id)})

    async def message_remove_media(self, message_id: int | str, media_id: int | str) -> dict:
        """Remove media from a message."""
        return await self._http.message_remove_media({
            "message_id": str(message_id),
            "media_id": str(media_id),
        })

    async def message_soft_erase(self, message_id: int | str) -> dict:
        """Soft-delete a message (can be recovered)."""
        return await self._http.message_soft_erase({"message_id": str(message_id)})

    # ── Moderation ──

    async def moderation_kickban(self, community_id: int | str, member_id: int | str,
                                  reason: str = "", duration: int | None = None) -> dict:
        """Kick/ban a member from a community."""
        payload = {
            "community_id": str(community_id),
            "member_id": str(member_id),
            "reason": reason,
        }
        if duration is not None:
            payload["duration"] = duration
        return await self._http.moderation_kickban(payload)

    # ── Notifications ──

    async def notification_read_all(self) -> dict:
        """Mark all notifications as read."""
        return await self._http.notification_read_all({})

    async def notification_read(self, notification_id: int | str) -> dict:
        """Mark a notification as read."""
        return await self._http.notification_read({"notification_id": str(notification_id)})

    async def notification_remove_all(self) -> dict:
        """Remove all notifications."""
        return await self._http.notification_remove_all({})

    async def notification_remove(self, notification_id: int | str) -> dict:
        """Remove a notification."""
        return await self._http.notification_remove({"notification_id": str(notification_id)})

    async def notification_subscribe(self, entity_type: str, entity_id: int | str) -> dict:
        """Subscribe to notifications for an entity."""
        return await self._http.notification_subscribe({
            "entity_type": entity_type,
            "entity_id": str(entity_id),
        })

    # ── Role (expanded) ──

    async def edit_role(self, role_id: int | str, name: str | None = None,
                        description: str | None = None, permissions: dict | None = None,
                        visible: int | None = None, highlightable: int | None = None,
                        tracked: int | None = None, color: str | None = None) -> dict:
        """Edit an existing role."""
        payload = {"role_id": str(role_id)}
        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if permissions is not None:
            payload["permissions"] = permissions
        if visible is not None:
            payload["visible"] = visible
        if highlightable is not None:
            payload["highlightable"] = highlightable
        if tracked is not None:
            payload["tracked"] = tracked
        if color is not None:
            payload["color"] = color
        return await self._http.edit_role(payload)

    async def remove_role(self, role_id: int | str) -> dict:
        """Remove/delete a role."""
        return await self._http.remove_role({"role_id": str(role_id)})

    # ── Search (expanded) ──

    async def search_content_simple(self, text: str, community_id: int | str = "1", page: int = 1) -> dict:
        """Simple content search (less filters than extended)."""
        return await self._http.search_content_simple({
            "community_id": str(community_id),
            "text": text,
            "page": page,
        })

    async def search_member_autocomplete(self, text: str, community_id: int | str | None = None,
                                          ignore_self: bool = True) -> dict:
        """Autocomplete member search (alias for search_users at HTTP level)."""
        return await self._http.search_users({
            "community_id": str(community_id) if community_id else None,
            "text": text,
            "ignore_self": ignore_self,
        })

    # ── Blocklist (expanded) ──

    async def blocklist_get(self) -> dict:
        """Get the full blocklist with member details."""
        return await self._http.blocklist_get({})

    async def blocklist_ids(self) -> dict:
        """Get only the IDs on the blocklist."""
        return await self._http.blocklist_ids({})

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


    # --- V2 API ---

    async def v2_bookmark_add(self, entity_type: str, entity_id: str | int, folder_id: str | int | None = None) -> dict:
        """Add a bookmark for an entity (lobby, thread, etc.)."""
        payload: dict = {"entity_type": entity_type, "entity_id": str(entity_id)}
        if folder_id is not None:
            payload["folder_id"] = str(folder_id)
        return await self._http.v2_bookmark_add(payload)


    async def v2_bookmark_list(self, community_id: str | int | None = None) -> dict:
        """List all bookmarks, optionally filtered by community."""
        payload: dict = {}
        if community_id is not None:
            payload["community_id"] = str(community_id)
        return await self._http.v2_bookmark_list(payload)


    async def v2_bookmark_move(self, bookmark_id: str | int, folder_id: str | int) -> dict:
        """Move a bookmark to a different folder."""
        return await self._http.v2_bookmark_move({
            "bookmark_id": str(bookmark_id),
            "folder_id": str(folder_id),
        })


    async def v2_bookmark_remove(self, bookmark_id: str | int) -> dict:
        """Remove a bookmark."""
        return await self._http.v2_bookmark_remove({"bookmark_id": str(bookmark_id)})


    async def v2_bookmark_rename(self, bookmark_id: str | int, name: str) -> dict:
        """Rename a bookmark."""
        return await self._http.v2_bookmark_rename({
            "bookmark_id": str(bookmark_id),
            "name": name,
        })

    # ─── V2 Community methods ────────────────────────────────────────────


    async def v2_community_list(self) -> dict:
        """List all communities."""
        return await self._http.v2_community_list({})


    async def v2_community_members(self, community_id: str | int, page: int = 1,
                                   pagesize: int = 12, sort: str = "displayname",
                                   sort_descending: int = 0) -> dict:
        """List members of a community with pagination."""
        return await self._http.v2_community_members({
            "community_id": str(community_id),
            "page": page,
            "pagesize": pagesize,
            "sort": sort,
            "sort_descending": sort_descending,
        })


    async def v2_community_my_roles(self, community_id: str | int) -> dict:
        """Get the current user's roles in a community."""
        return await self._http.v2_community_my_roles({"community_id": str(community_id)})


    async def v2_community_roles(self, community_id: str | int) -> dict:
        """Get all roles for a community."""
        return await self._http.v2_community_roles({"community_id": str(community_id)})


    async def v2_community_role_create(self, community_id: str | int, name: str,
                                       description: str = "", permissions: dict | None = None,
                                       visible: int = 1, highlightable: int = 0,
                                       tracked: int = 0, color: str = "919191") -> dict:
        """Create a new role in a community."""
        return await self._http.v2_community_role_create({
            "community_id": str(community_id),
            "name": name,
            "description": description,
            "permissions": permissions or {},
            "visible": visible,
            "highlightable": highlightable,
            "tracked": tracked,
            "color": color,
        })


    async def v2_community_role_edit(self, role_id: str | int, name: str | None = None,
                                     description: str | None = None,
                                     permissions: dict | None = None,
                                     visible: int | None = None,
                                     highlightable: int | None = None,
                                     tracked: int | None = None,
                                     color: str | None = None) -> dict:
        """Edit an existing role."""
        payload: dict = {"role_id": str(role_id)}
        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if permissions is not None:
            payload["permissions"] = permissions
        if visible is not None:
            payload["visible"] = visible
        if highlightable is not None:
            payload["highlightable"] = highlightable
        if tracked is not None:
            payload["tracked"] = tracked
        if color is not None:
            payload["color"] = color
        return await self._http.v2_community_role_edit(payload)


    async def v2_community_role_remove(self, role_id: str | int) -> dict:
        """Remove a role from a community."""
        return await self._http.v2_community_role_remove({"role_id": str(role_id)})


    async def v2_community_role_reorder(self, community_id: str | int,
                                        source_role_id: str | int,
                                        target_role_id: str | int) -> dict:
        """Reorder a role within a community."""
        return await self._http.v2_community_role_reorder({
            "community_id": str(community_id),
            "source_role_id": str(source_role_id),
            "target_role_id": str(target_role_id),
        })


    async def v2_community_emojis(self, community_id: str | int) -> dict:
        """Get all custom emojis for a community."""
        return await self._http.v2_community_emojis({"community_id": str(community_id)})


    async def v2_community_emoji_create(self, community_id: str | int, name: str,
                                        media_id: str | int) -> dict:
        """Create a custom emoji from an uploaded media file."""
        return await self._http.v2_community_emoji_create({
            "community_id": str(community_id),
            "name": name,
            "media_id": str(media_id),
        })


    async def v2_community_emoji_remove(self, community_id: str | int,
                                        emoji_id: str | int) -> dict:
        """Remove a custom emoji from a community."""
        return await self._http.v2_community_emoji_remove({
            "community_id": str(community_id),
            "emoji_id": str(emoji_id),
        })


    async def v2_community_emoji_upload(self, file_path: str, community_id: str | int,
                                        filename: str | None = None,
                                        content_type: str | None = None) -> dict:
        """Upload an emoji image file for a community."""
        return await self._http.v2_community_emoji_upload(
            file_path, str(community_id), filename=filename, content_type=content_type
        )


    async def v2_community_member_profile(self, community_id: str | int,
                                          nickname: str) -> dict:
        """Fetch a member's profile within a specific community."""
        return await self._http.v2_community_member_profile(str(community_id), nickname)

    # ─── V2 Forum methods ────────────────────────────────────────────────


    async def v2_forum_channel_list(self, community_id: str | int) -> dict:
        """List all forum channels in a community."""
        return await self._http.v2_forum_channel_list({"community_id": str(community_id)})


    async def v2_forum_channel_move(self, channel_id: str | int,
                                    group_id: str | int) -> dict:
        """Move a forum channel to a different group."""
        return await self._http.v2_forum_channel_move({
            "channel_id": str(channel_id),
            "group_id": str(group_id),
        })


    async def v2_forum_channel_reorder(self, community_id: str | int,
                                       channel_id: str | int,
                                       position: int) -> dict:
        """Reorder a forum channel within its group."""
        return await self._http.v2_forum_channel_reorder({
            "community_id": str(community_id),
            "channel_id": str(channel_id),
            "position": position,
        })


    async def v2_forum_channel_threads(self, channel_id: str | int, page: int = 1,
                                       sort: str = "hot",
                                       label_id: str | int | None = None) -> dict:
        """List threads in a forum channel with pagination."""
        return await self._http.v2_forum_channel_threads({
            "channel_id": str(channel_id),
            "page": page,
            "sort": sort,
            "label_id": str(label_id) if label_id else None,
        })


    async def v2_forum_channel_group_list(self, community_id: str | int) -> dict:
        """List all channel groups in a community."""
        return await self._http.v2_forum_channel_group_list({"community_id": str(community_id)})


    async def v2_forum_channel_group_move(self, group_id: str | int,
                                          position: int) -> dict:
        """Move a channel group to a new position."""
        return await self._http.v2_forum_channel_group_move({
            "group_id": str(group_id),
            "position": position,
        })


    async def v2_forum_channel_group_reorder(self, community_id: str | int,
                                             group_id: str | int,
                                             position: int) -> dict:
        """Reorder a channel group within a community."""
        return await self._http.v2_forum_channel_group_reorder({
            "community_id": str(community_id),
            "group_id": str(group_id),
            "position": position,
        })


    async def v2_forum_thread_get(self, thread_id: str | int) -> dict:
        """Get a forum thread by ID."""
        return await self._http.v2_forum_thread_get({"thread_id": str(thread_id)})

    # ─── V2 Game methods ─────────────────────────────────────────────────


    async def v2_game_party(self) -> dict:
        """Get the current game party information."""
        return await self._http.v2_game_party({})

    # ─── V2 Identity methods ─────────────────────────────────────────────


    async def v2_get_identity_infos(self, member_ids: list[str | int]) -> dict:
        """Get identity information for multiple members."""
        return await self._http.v2_get_identity_infos({
            "member_ids": [str(m) for m in member_ids],
        })

    # ─── V2 Guide methods ────────────────────────────────────────────────


    async def v2_guide_me(self) -> dict:
        """Get the current user's guide profile."""
        return await self._http.v2_guide_me({})


    async def v2_guide_register(self, topics: list[str], languages: list[str],
                                description: str = "") -> dict:
        """Register as a guide."""
        return await self._http.v2_guide_register({
            "topics": topics,
            "languages": languages,
            "description": description,
        })


    async def v2_guide_deregister(self) -> dict:
        """Deregister as a guide."""
        return await self._http.v2_guide_deregister({})


    async def v2_guide_profile_update(self, topics: list[str] | None = None,
                                      languages: list[str] | None = None,
                                      description: str | None = None) -> dict:
        """Update the current user's guide profile."""
        payload: dict = {}
        if topics is not None:
            payload["topics"] = topics
        if languages is not None:
            payload["languages"] = languages
        if description is not None:
            payload["description"] = description
        return await self._http.v2_guide_profile_update(payload)


    async def v2_guide_registration_criteria_check(self) -> dict:
        """Check if the current user meets guide registration criteria."""
        return await self._http.v2_guide_registration_criteria_check({})


    async def v2_guide_request_create(self, topic: str, language: str,
                                      description: str = "") -> dict:
        """Create a new guide help request."""
        return await self._http.v2_guide_request_create({
            "topic": topic,
            "language": language,
            "description": description,
        })


    async def v2_guide_request_incoming(self) -> dict:
        """List incoming guide requests (for guides)."""
        return await self._http.v2_guide_request_incoming({})


    async def v2_guide_request_outgoing(self) -> dict:
        """List outgoing guide requests (for seekers)."""
        return await self._http.v2_guide_request_outgoing({})


    async def v2_guide_request_remove_all(self) -> dict:
        """Remove all pending guide requests."""
        return await self._http.v2_guide_request_remove_all({})


    async def v2_guide_request_accept(self, request_id: str | int) -> dict:
        """Accept a guide request."""
        return await self._http.v2_guide_request_accept(str(request_id))


    async def v2_guide_request_cancel(self, request_id: str | int) -> dict:
        """Cancel a guide request."""
        return await self._http.v2_guide_request_cancel(str(request_id))


    async def v2_guide_request_decline(self, request_id: str | int) -> dict:
        """Decline a guide request."""
        return await self._http.v2_guide_request_decline(str(request_id))


    async def v2_guide_request_remove(self, request_id: str | int) -> dict:
        """Remove a guide request."""
        return await self._http.v2_guide_request_remove(str(request_id))


    async def v2_guide_search(self, topic: str | None = None,
                              language: str | None = None,
                              page: int = 1) -> dict:
        """Search for available guides."""
        payload: dict = {"page": page}
        if topic is not None:
            payload["topic"] = topic
        if language is not None:
            payload["language"] = language
        return await self._http.v2_guide_search(payload)


    async def v2_guide_session_active(self) -> dict:
        """Get the current active guide session."""
        return await self._http.v2_guide_session_active({})


    async def v2_guide_session_endorse(self, session_id: str | int) -> dict:
        """Endorse a guide after a session."""
        return await self._http.v2_guide_session_endorse(str(session_id))


    async def v2_guide_session_endorse_decline(self, session_id: str | int) -> dict:
        """Decline to endorse a guide after a session."""
        return await self._http.v2_guide_session_endorse_decline(str(session_id))


    async def v2_guide_session_terminate(self, session_id: str | int) -> dict:
        """Terminate an active guide session."""
        return await self._http.v2_guide_session_terminate(str(session_id))


    async def v2_guide_stats(self) -> dict:
        """Get guide statistics."""
        return await self._http.v2_guide_stats({})


    async def v2_guide_topic_list(self) -> dict:
        """List available guide topics."""
        return await self._http.v2_guide_topic_list({})

    # ─── V2 Lobby methods ────────────────────────────────────────────────


    async def v2_lobby_public_list(self, community_id: str | int) -> dict:
        """List public lobbies in a community."""
        return await self._http.v2_lobby_public_list({"community_id": str(community_id)})


    async def v2_lobby_public_move(self, lobby_id: str | int, position: int) -> dict:
        """Move a public lobby to a new position."""
        return await self._http.v2_lobby_public_move({
            "lobby_id": str(lobby_id),
            "position": position,
        })


    async def v2_lobby_public_reorder(self, community_id: str | int,
                                      lobby_id: str | int,
                                      position: int) -> dict:
        """Reorder a public lobby within a community."""
        return await self._http.v2_lobby_public_reorder({
            "community_id": str(community_id),
            "lobby_id": str(lobby_id),
            "position": position,
        })


    async def v2_lobby_group_list(self) -> dict:
        """List group lobbies (group messages)."""
        return await self._http.v2_lobby_group_list({})


    async def v2_lobby_private_list(self) -> dict:
        """List private lobbies (direct messages)."""
        return await self._http.v2_lobby_private_list({})


    async def v2_lobby_private_close(self, lobby_id: str | int) -> dict:
        """Close a private lobby."""
        return await self._http.v2_lobby_private_close({"lobby_id": str(lobby_id)})


    async def v2_lobby_private_open(self, member_ids: list[str | int]) -> dict:
        """Open a private lobby with specified members."""
        return await self._http.v2_lobby_private_open({
            "member_ids": [str(m) for m in member_ids],
        })


    async def v2_lobby_chats_list(self, page: int = 1, pagesize: int = 20) -> dict:
        """List chat lobbies with pagination."""
        return await self._http.v2_lobby_chats_list({
            "page": page,
            "pagesize": pagesize,
        })


    async def v2_lobby_chats_search(self, text: str, page: int = 1) -> dict:
        """Search chat lobbies by text."""
        return await self._http.v2_lobby_chats_search({
            "text": text,
            "page": page,
        })

    # ─── V2 Member methods ───────────────────────────────────────────────


    async def v2_member_profile(self, member_id: str | int) -> dict:
        """Get a member's profile."""
        return await self._http.v2_member_profile({"member_id": str(member_id)})


    async def v2_member_role_add(self, member_id: str | int,
                                 role_id: str | int) -> dict:
        """Add a role to a member."""
        return await self._http.v2_member_role_add({
            "member_id": str(member_id),
            "role_id": str(role_id),
        })


    async def v2_member_role_remove(self, member_id: str | int,
                                    role_id: str | int) -> dict:
        """Remove a role from a member."""
        return await self._http.v2_member_role_remove({
            "member_id": str(member_id),
            "role_id": str(role_id),
        })


    async def v2_member_role_set(self, member_id: str | int,
                                 role_ids: list[str | int]) -> dict:
        """Set all roles for a member (replaces existing roles)."""
        return await self._http.v2_member_role_set({
            "member_id": str(member_id),
            "role_ids": [str(r) for r in role_ids],
        })


    async def v2_member_settings(self) -> dict:
        """Get the current user's member settings."""
        return await self._http.v2_member_settings({})


    async def v2_member_settings_save(self, settings: dict) -> dict:
        """Save member settings."""
        return await self._http.v2_member_settings_save({"settings": settings})

    # ─── V2 Message methods ──────────────────────────────────────────────


    async def v2_message_send(self, lobby_id: str | int, content_blocks: list[dict],
                              plaintext: str = "") -> dict:
        """Send a message to a lobby via the V2 API."""
        return await self._http.v2_message_send({
            "lobby_id": str(lobby_id),
            "content_blocks": content_blocks,
            "plaintext": plaintext,
        })

    # ─── V2 Moderation methods ───────────────────────────────────────────


    async def v2_moderation_kickban(self, community_id: str | int,
                                    member_id: str | int, action: str,
                                    reason: str = "",
                                    duration: int | None = None) -> dict:
        """Kick or ban a member from a community.

        Args:
            community_id: The community to moderate in.
            member_id: The member to kick/ban.
            action: One of 'kick', 'ban', etc.
            reason: Reason for the moderation action.
            duration: Optional ban duration in seconds.
        """
        payload: dict = {
            "community_id": str(community_id),
            "member_id": str(member_id),
            "action": action,
            "reason": reason,
            "duration": duration,
        }
        return await self._http.v2_moderation_kickban(payload)

    # ─── V2 Search methods ───────────────────────────────────────────────


    async def v2_search_member_mapping(self, community_id: str | int, text: str,
                                       page: int = 1) -> dict:
        """Search for members with mapping information."""
        return await self._http.v2_search_member_mapping({
            "community_id": str(community_id),
            "text": text,
            "page": page,
        })

    # ─── End V2 methods ──────────────────────────────────────────────────



    async def identify(self):
        return await self._http.identify()

    async def fetch_embed(self, url: str) -> dict:
        """Fetch embed/media data for a URL (image, link preview, etc.)."""
        return await self._http.fetch_embed(url)

    async def upload_image(self, file_path: str, filename: str | None = None, content_type: str | None = None) -> Upload:
        """Upload an image to Spectrum. Returns an Upload object that can be passed directly to ContentBuilder.image()."""
        data = await self._http.upload_image(file_path, filename=filename, content_type=content_type)
        return Upload(data)

    async def close(self):
        await self._http.close()
