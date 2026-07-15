import asyncio
import base64
import json
import logging
import os

import aiohttp
import yarl

from .errors import HTTPError, NullResponseError, exception_map

IDENTIFY_URL = yarl.URL("https://robertsspaceindustries.com/api/spectrum/auth/identify")
SPECTRUM_API_BASE = "https://robertsspaceindustries.com/"
CREATE_MESSAGE_ENDPOINT = "/api/spectrum/message/create"
FETCH_THREADS = "/api/spectrum/forum/channel/threads"
CREATE_REPLY = "/api/spectrum/forum/thread/reply/create"
CREATE_THREAD = "/api/spectrum/forum/thread/create"
FETCH_PRESENCES_ENDPOINT = "/api/spectrum/lobby/presences"
FETCH_THREAD_NESTED = "/api/spectrum/forum/thread/nested"
FETCH_THREAD_CLASSIC = "/api/spectrum/forum/thread/classic"
FETCH_HISTORY = "/api/spectrum/message/history"
FETCH_MEMBER_BY_ID = "/api/spectrum/member/info/id"
FETCH_MEMBER_BY_HANDLE = "/api/spectrum/member/info/nickname"
FETCH_MEMBER_ROLES = "/api/spectrum/member/roles"
FETCH_MEMBER_COUNTERS = "/api/spectrum/member/counters"
FETCH_BROADCAST_MESSAGE_LIST = "/api/spectrum/broadcast-message/list"
FETCH_EMOJIS = "/api/spectrum/community/fetch-emojis"
FETCH_MOTD = "/api/spectrum/lobby/getMotd"
EXTENDED_SEARCH = "/api/spectrum/search/content/extended"
ADD_VOTE = "/api/spectrum/vote/add"
REMOVE_VOTE = "/api/spectrum/vote/remove"
ADD_REACTION = "/api/spectrum/reaction/add"
REMOVE_REACTION = "/api/spectrum/reaction/remove"
FETCH_ONLINE_MEMBERS_COUNT = "/api/spectrum/lobby/online-members-count"
SINK_THREADS = "/api/spectrum/forum/thread/bulk/sink"
PIN_THREADS = "/api/spectrum/forum/thread/bulk/pin"
CLOSE_THREADS = "/api/spectrum/forum/thread/bulk/lock"
DELETE_THREADS = "/api/spectrum/forum/thread/bulk/erase"
CREATE_CATEGORIES_GROUP = "/api/spectrum/forum/channel/group/create"
EDIT_CATEGORIES_GROUP = "/api/spectrum/forum/channel/group/edit"
CREATE_CATEGORY = "/api/spectrum/forum/channel/create"
EDIT_CATEGORY = "/api/spectrum/forum/channel/edit"
CREATE_LOBBY = "/api/spectrum/lobby/create"
EDIT_LOBBY = "/api/spectrum/lobby/edit"
FETCH_COMMUNITY_MEMBERS = "/api/spectrum/community/members"
ADD_MEMBER_ROLE = "/api/spectrum/member/role/add"
REMOVE_MEMBER_ROLE = "/api/spectrum/member/role/remove"
CREATE_ROLE = "/api/spectrum/role/create"
MOVE_ROLE = "/api/spectrum/role/move"
SEARCH_USERS = "/api/spectrum/search/member/autocomplete"
FETCH_LOBBY_INFO = "/api/spectrum/lobby/info"
SET_STATUS = "/api/spectrum/member/presence/setStatus"
EDIT_MESSAGE = "/api/spectrum/message/edit"
DELETE_MESSAGE = "/api/spectrum/message/delete"
ADD_FRIEND = "/api/spectrum/friend/add"
REMOVE_FRIEND = "/api/spectrum/friend/remove"
BLOCKLIST_ADD = "/api/spectrum/blocklist/add"
BLOCKLIST_REMOVE = "/api/spectrum/blocklist/remove"
UNSUBSCRIBE = "/api/spectrum/subscription/remove"

# V2 Endpoints
V2_BOOKMARK_ADD = "/api/spectrum/v2/bookmark/add"
V2_BOOKMARK_LIST = "/api/spectrum/v2/bookmark/list"
V2_BOOKMARK_MOVE = "/api/spectrum/v2/bookmark/move"
V2_BOOKMARK_REMOVE = "/api/spectrum/v2/bookmark/remove"
V2_BOOKMARK_RENAME = "/api/spectrum/v2/bookmark/rename"
V2_COMMUNITY_LIST = "/api/spectrum/v2/community/list"
V2_COMMUNITY_MEMBERS = "/api/spectrum/v2/community/members"
V2_COMMUNITY_MY_ROLES = "/api/spectrum/v2/community/my-roles"
V2_COMMUNITY_ROLES = "/api/spectrum/v2/community/roles"
V2_COMMUNITY_ROLE_CREATE = "/api/spectrum/v2/community/role/create"
V2_COMMUNITY_ROLE_EDIT = "/api/spectrum/v2/community/role/edit"
V2_COMMUNITY_ROLE_REMOVE = "/api/spectrum/v2/community/role/remove"
V2_COMMUNITY_ROLE_REORDER = "/api/spectrum/v2/community/role/reorder"
V2_COMMUNITY_EMOJIS = "/api/spectrum/v2/community/emojis"
V2_COMMUNITY_EMOJI_CREATE = "/api/spectrum/v2/community/emoji/create"
V2_COMMUNITY_EMOJI_REMOVE = "/api/spectrum/v2/community/emoji/remove"
V2_COMMUNITY_EMOJI_UPLOAD = "/api/spectrum/v2/community/emoji/upload"
V2_FORUM_CHANNEL_LIST = "/api/spectrum/v2/forum/channel/list"
V2_FORUM_CHANNEL_MOVE = "/api/spectrum/v2/forum/channel/move"
V2_FORUM_CHANNEL_REORDER = "/api/spectrum/v2/forum/channel/reorder"
V2_FORUM_CHANNEL_THREADS = "/api/spectrum/v2/forum/channel/threads"
V2_FORUM_CHANNEL_GROUP_LIST = "/api/spectrum/v2/forum/channel/group/list"
V2_FORUM_CHANNEL_GROUP_MOVE = "/api/spectrum/v2/forum/channel/group/move"
V2_FORUM_CHANNEL_GROUP_REORDER = "/api/spectrum/v2/forum/channel/group/reorder"
V2_FORUM_THREAD_GET = "/api/spectrum/v2/forum/thread/get"
V2_GAME_PARTY = "/api/spectrum/v2/game/party"
V2_GET_IDENTITY_INFOS = "/api/spectrum/v2/getIdentityInfos"
V2_GUIDE_ME = "/api/spectrum/v2/guide/me"
V2_GUIDE_REGISTER = "/api/spectrum/v2/guide/register"
V2_GUIDE_DEREGISTER = "/api/spectrum/v2/guide/deregister"
V2_GUIDE_PROFILE_UPDATE = "/api/spectrum/v2/guide/profile/update"
V2_GUIDE_REGISTRATION_CRITERIA_CHECK = "/api/spectrum/v2/guide/registration/criteria/check"
V2_GUIDE_REQUEST_CREATE = "/api/spectrum/v2/guide/request/create"
V2_GUIDE_REQUEST_INCOMING = "/api/spectrum/v2/guide/request/incoming"
V2_GUIDE_REQUEST_OUTGOING = "/api/spectrum/v2/guide/request/outgoing"
V2_GUIDE_REQUEST_REMOVE_ALL = "/api/spectrum/v2/guide/request/remove-all"
V2_GUIDE_SEARCH = "/api/spectrum/v2/guide/search"
V2_GUIDE_SESSION_ACTIVE = "/api/spectrum/v2/guide/session/active"
V2_GUIDE_STATS = "/api/spectrum/v2/guide/stats"
V2_GUIDE_TOPIC_LIST = "/api/spectrum/v2/guide/topic/list"
V2_LOBBY_PUBLIC_LIST = "/api/spectrum/v2/lobby/public/list"
V2_LOBBY_PUBLIC_MOVE = "/api/spectrum/v2/lobby/public/move"
V2_LOBBY_PUBLIC_REORDER = "/api/spectrum/v2/lobby/public/reorder"
V2_LOBBY_GROUP_LIST = "/api/spectrum/v2/lobby/group/list"
V2_LOBBY_PRIVATE_LIST = "/api/spectrum/v2/lobby/private/list"
V2_LOBBY_PRIVATE_CLOSE = "/api/spectrum/v2/lobby/private/close"
V2_LOBBY_PRIVATE_OPEN = "/api/spectrum/v2/lobby/private/open"
V2_LOBBY_CHATS_LIST = "/api/spectrum/v2/lobby/chats/list"
V2_LOBBY_CHATS_SEARCH = "/api/spectrum/v2/lobby/chats/search"
V2_MEMBER_PROFILE = "/api/spectrum/v2/member/profile"
V2_MEMBER_ROLE_ADD = "/api/spectrum/v2/member/role/add"
V2_MEMBER_ROLE_REMOVE = "/api/spectrum/v2/member/role/remove"
V2_MEMBER_ROLE_SET = "/api/spectrum/v2/member/role/set"
V2_MEMBER_SETTINGS = "/api/spectrum/v2/member/settings"
V2_MEMBER_SETTINGS_SAVE = "/api/spectrum/v2/member/settings/save"
V2_MESSAGE_SEND = "/api/spectrum/v2/message/send"
V2_MODERATION_KICKBAN = "/api/spectrum/v2/moderation/kickban"
V2_SEARCH_MEMBER_MAPPING = "/api/spectrum/v2/search/member/mapping"


# Bookmarks
BOOKMARK_MOVE = "/api/spectrum/bookmark/move"
BOOKMARK_REMOVE = "/api/spectrum/bookmark/remove"
BOOKMARK_RENAME = "/api/spectrum/bookmark/rename"
BOOKMARKS_LIST = "/api/spectrum/bookmarks"

# Broadcast Messages
BROADCAST_MESSAGE_CREATE = "/api/spectrum/broadcast-message/create"
BROADCAST_MESSAGE_EDIT = "/api/spectrum/broadcast-message/edit"
BROADCAST_MESSAGE_REMOVE = "/api/spectrum/broadcast-message/remove"

# Emoji
EMOJI_CREATE = "/api/spectrum/emoji/create"
EMOJI_ERASE = "/api/spectrum/emoji/erase"
UPLOAD_EMOJI = "/api/spectrum/media/upload/emoji"

# Flag / Report
FLAG_CONTENT = "/api/spectrum/flag/"

# Forum Channel CRUD
ERASE_CATEGORY = "/api/spectrum/forum/channel/erase"
ERASE_CATEGORIES_GROUP = "/api/spectrum/forum/channel/group/erase"
MOVE_CATEGORIES_GROUP = "/api/spectrum/forum/channel/group/move"
MOVE_CATEGORY = "/api/spectrum/forum/channel/move"

# Forum Thread Bulk Ops
EDIT_THREADS = "/api/spectrum/forum/thread/bulk/edit"
UNLOCK_THREADS = "/api/spectrum/forum/thread/bulk/unlock"
UNPIN_THREADS = "/api/spectrum/forum/thread/bulk/unpin"
UNSINK_THREADS = "/api/spectrum/forum/thread/bulk/unsink"

# Forum Thread Single Ops
EDIT_THREAD = "/api/spectrum/forum/thread/edit"
ERASE_THREAD = "/api/spectrum/forum/thread/erase"

# Forum Replies
FETCH_THREAD_REPLIES = "/api/spectrum/forum/thread/replies/"
FETCH_THREAD_REPLY = "/api/spectrum/forum/thread/reply"
FETCH_REPLY_CHILDREN = "/api/spectrum/forum/thread/reply/childrens"
EDIT_REPLY = "/api/spectrum/forum/thread/reply/edit"
ERASE_REPLY = "/api/spectrum/forum/thread/reply/erase"

# Friends
FRIEND_REQUEST_ACCEPT = "/api/spectrum/friend-request/accept"
FRIEND_REQUEST_CANCEL = "/api/spectrum/friend-request/cancel"
FRIEND_REQUEST_CREATE = "/api/spectrum/friend-request/create"
FRIEND_REQUEST_DECLINE = "/api/spectrum/friend-request/decline"
FRIEND_REQUEST_LIST = "/api/spectrum/friend-request/list"
FRIEND_LIST = "/api/spectrum/friend/list"
FRIEND_SEARCH = "/api/spectrum/friend/search"

# Guide System
GUIDE_DEREGISTER = "/api/spectrum/guide/deregister"
GUIDE_ENDORSEMENT_CREATE = "/api/spectrum/guide/endorsement/create"
GUIDE_ENDORSEMENT_DECLINE = "/api/spectrum/guide/endorsement/decline"
GUIDE_PROFILE_UPDATE = "/api/spectrum/guide/profile/update"
GUIDE_REGISTER = "/api/spectrum/guide/register"
GUIDE_REGISTRATION_CRITERIA = "/api/spectrum/guide/registration/criteria"
GUIDE_REQUEST_ACCEPT = "/api/spectrum/guide/request/accept"
GUIDE_REQUEST_CANCEL = "/api/spectrum/guide/request/cancel"
GUIDE_REQUEST_CREATE = "/api/spectrum/guide/request/create"
GUIDE_REQUEST_DECLINE = "/api/spectrum/guide/request/decline"
GUIDE_REQUEST_REMOVE = "/api/spectrum/guide/request/remove"
GUIDE_REQUEST_REMOVE_ALL = "/api/spectrum/guide/request/removeAll"
GUIDE_SEARCH = "/api/spectrum/guide/search"
GUIDE_SESSION_TERMINATE = "/api/spectrum/guide/session/terminate"
GUIDE_TOPICS_LIST = "/api/spectrum/guide/topics/list"

# Lobby (expanded)
LOBBY_ACCEPT_INVITE = "/api/spectrum/lobby/acceptInvite"
LOBBY_CANCEL_INVITE = "/api/spectrum/lobby/cancelInvite"
LOBBY_CLOSE_PRIVATE = "/api/spectrum/lobby/closePrivate"
LOBBY_DECLINE_INVITE = "/api/spectrum/lobby/declineInvite"
LOBBY_ERASE = "/api/spectrum/lobby/erase"
LOBBY_GUIDE_SESSION_HISTORY = "/api/spectrum/lobby/guideSessionHistory"
LOBBY_INVITE = "/api/spectrum/lobby/invite"
LOBBY_KICK = "/api/spectrum/lobby/kick"
LOBBY_LEAVE = "/api/spectrum/lobby/leave"
LOBBY_LIST_INVITES = "/api/spectrum/lobby/listInvites"
LOBBY_MOVE = "/api/spectrum/lobby/move"
LOBBY_TRANSFER_LEADERSHIP = "/api/spectrum/lobby/transferLeadership"

# Member (expanded)
MEMBER_SPOKEN_LANGUAGES = "/api/spectrum/member/spoken-languages"

# Message (expanded)
MESSAGE_ERASE = "/api/spectrum/message/erase"
MESSAGE_REMOVE_MEDIA = "/api/spectrum/message/removeMedia"
MESSAGE_SOFT_ERASE = "/api/spectrum/message/soft-erase"

# Moderation
MODERATION_KICKBAN = "/api/spectrum/moderation/kickban"

# Notifications
NOTIFICATION_READ_ALL = "/api/spectrum/notification/read-all"
NOTIFICATION_READ = "/api/spectrum/notification/read"
NOTIFICATION_REMOVE_ALL = "/api/spectrum/notification/remove-all"
NOTIFICATION_REMOVE = "/api/spectrum/notification/remove"
NOTIFICATION_SUBSCRIBE = "/api/spectrum/notification/subscribe"

# Role (expanded)
ROLE_EDIT = "/api/spectrum/role/edit"
ROLE_REMOVE = "/api/spectrum/role/remove"

# Search (expanded)
SEARCH_CONTENT_SIMPLE = "/api/spectrum/search/content/simple"

# Blocklist (expanded)
BLOCKLIST_GET = "/api/spectrum/blocklist"
BLOCKLIST_IDS = "/api/spectrum/blocklist/ids"


class InvalidTokenException(Exception):
    pass


log = logging.getLogger(__name__)


class HTTP:
    MAX_RETRIES = 3
    RETRY_BACKOFF = 1.0

    def __init__(self, client, rsi_token, device_id):
        self._client = client
        self._rsi_token = rsi_token
        self._gateway_token = None
        self._device_id = device_id
        self._client_id = None

        self._session = aiohttp.ClientSession(base_url=SPECTRUM_API_BASE)

        self.cookies = {
            '_rsi_device': self._device_id or "",
            'Rsi-Token': self._rsi_token or "",
        }

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://robertsspaceindustries.com/spectrum/community/SC/lobby/1',
            'Origin': 'https://robertsspaceindustries.com',
            'Connection': 'keep-alive',
            'DNT': '1',
        }

        if self._rsi_token:
            self.headers['X-Rsi-Token'] = self._rsi_token

    async def close(self):
        await self._session.close()

    async def send_message(self, payload: dict):
        return await self.make_request(CREATE_MESSAGE_ENDPOINT, payload)

    async def send_reply(self, payload: dict):
        """
        {"thread_id":"396239","parent_reply_id":"6452173","content_blocks":[{"id":1,"type":"text","data":{"blocks":[{"key":"6eoc5","text":"Replying","type":"unstyled","depth":0,"inlineStyleRanges":[],"entityRanges":[],"data":{}}],"entityMap":{}}}],"plaintext":"Replying","highlight_role_id":null}
        {"thread_id":"396239","parent_reply_id":null,"content_blocks":[{"id":1,"type":"text","data":{"blocks":[{"key":"5eehk","text":"Top level reply","type":"unstyled","depth":0,"inlineStyleRanges":[],"entityRanges":[],"data":{}}],"entityMap":{}}}],"plaintext":"Top level reply","highlight_role_id":null}
        """
        return await self.make_request(CREATE_MESSAGE_ENDPOINT, payload)

    async def create_thread(self, payload: dict):
        """
        {"type":"discussion","channel_id":"305988","label_id":null,"subject":"Create new thread","content_blocks":[{"id":1,"type":"text","data":{"blocks":[{"key":"dr2qu","text":"New thread","type":"unstyled","depth":0,"inlineStyleRanges":[],"entityRanges":[],"data":{}}],"entityMap":{}}}],"plaintext":"New thread","highlight_role_id":null,"is_locked":false,"is_reply_nesting_disabled":false}
        """
        has_images = any(b.get("type") == "image" for b in payload.get("content_blocks", []))
        max_attempts = 6 if has_images else 1
        for attempt in range(max_attempts):
            try:
                return await self._create_thread_request(payload)
            except HTTPError as e:
                if "Invalid image block data" in str(e) and attempt < max_attempts - 1:
                    log.warning("Image still processing, retrying in %ds (attempt %d/%d)", 3 * (attempt + 1), attempt + 1, max_attempts)
                    await asyncio.sleep(3 * (attempt + 1))
                    continue
                raise

    async def _create_thread_request(self, payload: dict):
        await self._client._ready_event.wait()
        headers = {**self.headers, 'X-Tavern-action-id': '1'}
        if self._client_id:
            headers['x-tavern-id'] = self._client_id

        async with self._session.post(
                CREATE_THREAD,
                json=payload,
                headers=headers,
                cookies=self.cookies
        ) as resp:
            response = await resp.json()
            if response is None:
                raise NullResponseError()
            elif response.get('success'):
                return response['data']
            else:
                data = response.get('data', {})
                detail = data.get('content_blocks', '') if isinstance(data, dict) else ''
                if detail:
                    raise HTTPError(detail)
                raise exception_map.get(response.get('code', ''), HTTPError)(response.get('msg', ''))

    async def sink_threads(self, payload: dict):
        """
        {"thread_ids":["396742"]}
        """
        return await self.make_request(SINK_THREADS, payload)

    async def pin_threads(self, payload: dict):
        """
        {"thread_ids":["396742"]}
        """
        return await self.make_request(PIN_THREADS, payload)

    async def close_threads(self, payload: dict):
        """
        {"thread_ids":["396742"],"reason":"It's done for"}
        """
        return await self.make_request(CLOSE_THREADS, payload)

    async def delete_threads(self, payload: dict):
        """
        {"thread_ids":["396742"],"reason":"Its done for"}
        """
        return await self.make_request(DELETE_THREADS, payload)

    async def fetch_threads(self, payload: dict):
        """
        {"channel_id":"305988","page":1,"sort":"hot","label_id":null}
        """
        return await self.make_request(FETCH_THREADS, payload)

    async def fetch_presences(self, payload):
        return await self.make_request(FETCH_PRESENCES_ENDPOINT, payload)

    async def fetch_history(self, payload):
        """
        {"lobby_id":"1","timeframe":"before","message_id":null,"size":50}
        """
        return await self.make_request(FETCH_HISTORY, payload)

    async def fetch_thread_nested(self, payload):
        """ {"slug":"limit-accessibility-to-ships-upon-full-release-of-","sort":"oldest","target_reply_id":"6389016"}
        sort by oldest, newest, votes
        """
        return await self.make_request(FETCH_THREAD_NESTED, payload)

    async def fetch_thread_classic(self, payload):
        """ {"slug":"limit-accessibility-to-ships-upon-full-release-of-","sort":"oldest","target_reply_id":"6389016"} """
        return await self.make_request(FETCH_THREAD_CLASSIC, payload)

    async def fetch_member_by_id(self, payload):
        """{member_id: "..."}"""
        return await self.make_request(FETCH_MEMBER_BY_ID, payload)

    async def fetch_member_by_handle(self, payload):
        """{nickname: "..."}"""
        return await self.make_request(FETCH_MEMBER_BY_HANDLE, payload)

    async def fetch_member_roles(self, payload):
        """{"member_id":"67063","community_id":"1"}"""
        return await self.make_request(FETCH_MEMBER_ROLES, payload)

    async def fetch_member_counters(self, payload):
        """{"member_id":"67063","community_id":"1"}"""
        return await self.make_request(FETCH_MEMBER_COUNTERS, payload)

    async def fetch_emojis(self, payload):
        """ {"community_id":"1"} """
        return await self.make_request(FETCH_EMOJIS, payload)

    async def add_vote(self, payload):
        """
        {"entity_type":"forum_thread_reply","entity_id":"6385009"}
        {"entity_type":"forum_thread","entity_id":"391573"}
        """
        return await self.make_request(ADD_VOTE, payload)

    async def remove_vote(self, payload):
        """
        {"entity_type":"forum_thread_reply","entity_id":"6385009"}
        {"entity_type":"forum_thread","entity_id":"391573"}
        """
        return await self.make_request(REMOVE_VOTE, payload)

    async def add_reaction(self, payload):
        """
        {"reaction_type":":-1:","entity_type":"forum_thread","entity_id":"391573"}
        """
        return await self.make_request(ADD_REACTION, payload)

    async def remove_reaction(self, payload):
        """
        {"entity_type":"forum_thread_reply","entity_id":"6385009"}
        {"entity_type":"forum_thread","entity_id":"391573"}
        """
        return await self.make_request(REMOVE_REACTION, payload)

    async def fetch_online_count(self, payload):
        """
        {"community_id":"100987"}
        """
        return await self.make_request(FETCH_ONLINE_MEMBERS_COUNT, payload)

    async def create_categories_group(self, payload):
        """
        {"community_id":"100987","name":"More Categories"}
        """
        return await self.make_request(CREATE_CATEGORIES_GROUP, payload)

    async def edit_categories_group(self, payload):
        """
        {"group_id":"112656","name":"More Categories 2"}
        """
        return await self.make_request(EDIT_CATEGORIES_GROUP, payload)

    async def create_category(self, payload):
        """
        {"community_id":"100987","group_id":"102761","name":"Cool category","description":"For things","color":"FF6262","sort_filter":null,"label_required":0}
        """
        return await self.make_request(CREATE_CATEGORY, payload)

    async def edit_category(self, payload):
        """
        {"channel_id":"335429","group_id":"112656","name":"Cool category 1","description":"For things 2","color":"63A3E6","sort_filter":null,"label_required":0,"permissions":{"660853":{"read":null,"create_thread":null,"create_thread_reply":null,"manage":null,"moderate":null},"660854":{"read":null,"create_thread":null,"create_thread_reply":null,"manage":true,"moderate":null},"660855":{"read":null,"create_thread":null,"create_thread_reply":null,"manage":null,"moderate":null},"660856":{"read":null,"create_thread":null,"create_thread_reply":null,"manage":null,"moderate":null},"660857":{"read":null,"create_thread":null,"create_thread_reply":null,"manage":null,"moderate":null},"660858":{"read":null,"create_thread":null,"create_thread_reply":null,"manage":null,"moderate":null},"660859":{"read":null,"create_thread":null,"create_thread_reply":null,"manage":null,"moderate":null},"727710":{"read":null,"create_thread":null,"create_thread_reply":null,"manage":null,"moderate":null}},"labels":[{"id":null,"name":"Epic tag"}]}
        """
        return await self.make_request(EDIT_CATEGORY, payload)

    async def create_lobby(self, payload):
        """
        {"community_id":"100987","name":"poggerslob","description":"123","color":"C197C8","type":"public"}
        """
        return await self.make_request(CREATE_LOBBY, payload)

    async def edit_lobby(self, payload):
        """
        {"lobby_id":"5852041","name":"poggerslob","description":"123123","color":"C197C8","type":"public","permissions":{"660853":{"read":null,"send_message":null,"manage":null,"moderate":null,"set_motd":null},"660854":{"read":null,"send_message":null,"manage":true,"moderate":null,"set_motd":true},"660855":{"read":null,"send_message":null,"manage":null,"moderate":null,"set_motd":null},"660856":{"read":null,"send_message":null,"manage":null,"moderate":null,"set_motd":null},"660857":{"read":null,"send_message":null,"manage":null,"moderate":null,"set_motd":null},"660858":{"read":null,"send_message":null,"manage":null,"moderate":null,"set_motd":null},"660859":{"read":null,"send_message":null,"manage":null,"moderate":null,"set_motd":null},"727710":{"read":null,"send_message":null,"manage":null,"moderate":null,"set_motd":null}}}
        """
        return await self.make_request(EDIT_LOBBY, payload)

    async def fetch_community_members(self, payload):
        """
        {"community_id":"100987","page":1,"pagesize":12,"sort":"displayname","sort_descending":0}
        """
        return await self.make_request(FETCH_COMMUNITY_MEMBERS, payload)

    async def add_member_role(self, payload):
        """
        {"member_id":"2291348","role_id":"727710"}
        """
        return await self.make_request(ADD_MEMBER_ROLE, payload)

    async def remove_member_role(self, payload):
        """
        {"member_id":"2291348","role_id":"727710"}
        """
        return await self.make_request(REMOVE_MEMBER_ROLE, payload)

    async def create_role(self, payload):
        """
        {"community_id":"100987","name":"New role","description":"With perms","permissions":{"global":{"manage_roles":false,"kick_members":false,"embed_link":false,"upload_media":false,"mention":false,"reaction":false,"vote":false,"read_erased":false},"message_lobby":{"read":true,"send_message":false,"manage":false,"moderate":false,"set_motd":false},"forum_channel":{"read":false,"create_thread":false,"create_thread_reply":false,"manage":false,"moderate":false},"custom_emoji":{"create":false,"remove":false}},"visible":1,"highlightable":0,"tracked":0,"color":"919191"}
        """
        return await self.make_request(CREATE_ROLE, payload)

    async def move_role(self, payload):
        """
        {"community_id":"100987","source_role_id":"660855","target_role_id":"660857"}
        """
        return await self.make_request(MOVE_ROLE, payload)

    async def search_users(self, payload):
        """
        {"community_id":null,"text":"nate4313","ignore_self":true}
        """
        return await self.make_request(SEARCH_USERS, payload)

    async def fetch_motd(self, payload):
        """
        {"lobby_id":"7"}
        """
        return await self.make_request(FETCH_MOTD, payload)

    async def set_motd(self, payload):
        """{"lobby_id":"5632276","motd":"Test motd"}"""
        return await self.make_request("/api/spectrum/lobby/setMotd", payload)

    async def fetch_lobby_info(self, payload):
        """
        {"member_id":"3100861"}
        """
        return await self.make_request(FETCH_LOBBY_INFO, payload)

    async def edit_message(self, payload):
        """{"message_id":"123","content_state":{...},"plaintext":"edited text","media_id":null}"""
        return await self.make_request(EDIT_MESSAGE, payload)

    async def delete_message(self, payload):
        """{"message_id":"123"}"""
        return await self.make_request(DELETE_MESSAGE, payload)

    async def add_friend(self, payload):
        """{"member_id":"123"}"""
        return await self.make_request(ADD_FRIEND, payload)

    async def remove_friend(self, payload):
        """{"member_id":"123"}"""
        return await self.make_request(REMOVE_FRIEND, payload)

    async def extended_search(self, payload):
        """{"community_id":"1","type":["op","reply","chat"],"text":"","page":1,"sort":"latest","range":"year","author":"200762","visibility":"nonerased"}"""
        return await self.make_request(EXTENDED_SEARCH, payload)

    async def blocklist_add(self, payload):
        """{"member_id":"48758"}"""
        return await self.make_request(BLOCKLIST_ADD, payload)

    async def blocklist_remove(self, payload):
        """{"member_id":"48758"}"""
        return await self.make_request(BLOCKLIST_REMOVE, payload)

    async def set_status(self, payload):
        """{"status":"playing","info":"Playing Star Citizen"}"""
        return await self.make_request(SET_STATUS, payload)

    async def unsubscribe(self, payload):
        """{"subscription_keys":["key1","key2"]}"""
        return await self.make_request(UNSUBSCRIBE, payload)

    # ── Bookmarks ──

    async def bookmark_move(self, payload: dict):
        """{"bookmark_id":"123","target_folder_id":"456","position":0}"""
        return await self.make_request(BOOKMARK_MOVE, payload)

    async def bookmark_remove(self, payload: dict):
        """{"bookmark_id":"123"}"""
        return await self.make_request(BOOKMARK_REMOVE, payload)

    async def bookmark_rename(self, payload: dict):
        """{"bookmark_id":"123","name":"New Name"}"""
        return await self.make_request(BOOKMARK_RENAME, payload)

    async def bookmarks_list(self, payload: dict):
        """{"community_id":"1"}"""
        return await self.make_request(BOOKMARKS_LIST, payload)

    # ── Broadcast Messages ──

    async def broadcast_message_create(self, payload: dict):
        """{"community_id":"1","content_blocks":[...],"plaintext":"Hello"}"""
        return await self.make_request(BROADCAST_MESSAGE_CREATE, payload)

    async def broadcast_message_edit(self, payload: dict):
        """{"broadcast_message_id":"123","content_blocks":[...],"plaintext":"Edited"}"""
        return await self.make_request(BROADCAST_MESSAGE_EDIT, payload)

    async def broadcast_message_remove(self, payload: dict):
        """{"broadcast_message_id":"123"}"""
        return await self.make_request(BROADCAST_MESSAGE_REMOVE, payload)

    # ── Emoji ──

    async def emoji_create(self, payload: dict):
        """{"community_id":"1","name":"emoji_name","media_id":"123"}"""
        return await self.make_request(EMOJI_CREATE, payload)

    async def emoji_erase(self, payload: dict):
        """{"community_id":"1","emoji_id":"123"}"""
        return await self.make_request(EMOJI_ERASE, payload)

    async def upload_emoji(self, file_path: str, filename: str = None, content_type: str = None):
        """Upload an emoji image to Spectrum. Returns the media data dict."""
        import mimetypes
        await self._client._ready_event.wait()

        if filename is None:
            filename = os.path.basename(file_path)
        if content_type is None:
            content_type = mimetypes.guess_type(file_path)[0] or "image/png"

        headers = {**self.headers}
        if self._client_id:
            headers['x-tavern-id'] = self._client_id

        data = aiohttp.FormData()
        data.add_field('file', open(file_path, 'rb'), filename=filename, content_type=content_type)

        async with self._session.post(
                UPLOAD_EMOJI,
                data=data,
                headers=headers,
                cookies=self.cookies
        ) as resp:
            response = await resp.json()
            if response is None:
                raise NullResponseError()
            elif response.get('success'):
                return response['data']
            else:
                raise exception_map.get(response.get('code', 0), HTTPError)(response.get('msg', 'Upload failed'))

    # ── Flag / Report ──

    async def flag_content(self, payload: dict):
        """{"entity_type":"message","entity_id":"123","reason":"spam","comment":"Spam message"}"""
        return await self.make_request(FLAG_CONTENT, payload)

    # ── Forum Channel CRUD ──

    async def erase_category(self, payload: dict):
        """{"channel_id":"335429"}"""
        return await self.make_request(ERASE_CATEGORY, payload)

    async def erase_categories_group(self, payload: dict):
        """{"group_id":"112656"}"""
        return await self.make_request(ERASE_CATEGORIES_GROUP, payload)

    async def move_categories_group(self, payload: dict):
        """{"community_id":"100987","source_group_id":"112656","target_group_id":"102761"}"""
        return await self.make_request(MOVE_CATEGORIES_GROUP, payload)

    async def move_category(self, payload: dict):
        """{"channel_id":"335429","target_group_id":"102761","position":0}"""
        return await self.make_request(MOVE_CATEGORY, payload)

    # ── Forum Thread Bulk Ops ──

    async def edit_threads(self, payload: dict):
        """{"thread_ids":["396742"],"label_id":"123","channel_id":"305988"}"""
        return await self.make_request(EDIT_THREADS, payload)

    async def unlock_threads(self, payload: dict):
        """{"thread_ids":["396742"]}"""
        return await self.make_request(UNLOCK_THREADS, payload)

    async def unpin_threads(self, payload: dict):
        """{"thread_ids":["396742"]}"""
        return await self.make_request(UNPIN_THREADS, payload)

    async def unsink_threads(self, payload: dict):
        """{"thread_ids":["396742"]}"""
        return await self.make_request(UNSINK_THREADS, payload)

    # ── Forum Thread Single Ops ──

    async def edit_thread(self, payload: dict):
        """{"thread_id":"396742","subject":"New Subject","content_blocks":[...],"plaintext":"New body","label_id":null,"is_locked":false,"is_reply_nesting_disabled":false}"""
        return await self.make_request(EDIT_THREAD, payload)

    async def erase_thread(self, payload: dict):
        """{"thread_id":"396742","reason":"Violates rules"}"""
        return await self.make_request(ERASE_THREAD, payload)

    # ── Forum Replies ──

    async def fetch_thread_replies(self, payload: dict):
        """{"thread_id":"396239","page":1,"sort":"oldest"}"""
        return await self.make_request(FETCH_THREAD_REPLIES, payload)

    async def fetch_thread_reply(self, payload: dict):
        """{"reply_id":"6452173"}"""
        return await self.make_request(FETCH_THREAD_REPLY, payload)

    async def fetch_reply_children(self, payload: dict):
        """{"reply_id":"6452173","page":1,"sort":"oldest"}"""
        return await self.make_request(FETCH_REPLY_CHILDREN, payload)

    async def edit_reply(self, payload: dict):
        """{"reply_id":"6452173","content_blocks":[...],"plaintext":"Edited reply"}"""
        return await self.make_request(EDIT_REPLY, payload)

    async def erase_reply(self, payload: dict):
        """{"reply_id":"6452173","reason":"Violates rules"}"""
        return await self.make_request(ERASE_REPLY, payload)

    # ── Friends (expanded) ──

    async def friend_request_accept(self, payload: dict):
        """{"member_id":"123"}"""
        return await self.make_request(FRIEND_REQUEST_ACCEPT, payload)

    async def friend_request_cancel(self, payload: dict):
        """{"member_id":"123"}"""
        return await self.make_request(FRIEND_REQUEST_CANCEL, payload)

    async def friend_request_create(self, payload: dict):
        """{"member_id":"123"}"""
        return await self.make_request(FRIEND_REQUEST_CREATE, payload)

    async def friend_request_decline(self, payload: dict):
        """{"member_id":"123"}"""
        return await self.make_request(FRIEND_REQUEST_DECLINE, payload)

    async def friend_request_list(self, payload: dict):
        """{}"""
        return await self.make_request(FRIEND_REQUEST_LIST, payload)

    async def friend_list(self, payload: dict):
        """{}"""
        return await self.make_request(FRIEND_LIST, payload)

    async def friend_search(self, payload: dict):
        """{"text":"nate"}"""
        return await self.make_request(FRIEND_SEARCH, payload)

    # ── Guide System ──

    async def guide_deregister(self, payload: dict):
        """{"community_id":"1"}"""
        return await self.make_request(GUIDE_DEREGISTER, payload)

    async def guide_endorsement_create(self, payload: dict):
        """{"guide_id":"123","comment":"Great guide"}"""
        return await self.make_request(GUIDE_ENDORSEMENT_CREATE, payload)

    async def guide_endorsement_decline(self, payload: dict):
        """{"endorsement_id":"123"}"""
        return await self.make_request(GUIDE_ENDORSEMENT_DECLINE, payload)

    async def guide_profile_update(self, payload: dict):
        """{"community_id":"1","bio":"Experienced pilot","topics":["combat","trading"]}"""
        return await self.make_request(GUIDE_PROFILE_UPDATE, payload)

    async def guide_register(self, payload: dict):
        """{"community_id":"1","topics":["combat","trading"],"bio":"I can help"}"""
        return await self.make_request(GUIDE_REGISTER, payload)

    async def guide_registration_criteria(self, payload: dict):
        """{"community_id":"1"}"""
        return await self.make_request(GUIDE_REGISTRATION_CRITERIA, payload)

    async def guide_request_accept(self, payload: dict):
        """{"request_id":"123"}"""
        return await self.make_request(GUIDE_REQUEST_ACCEPT, payload)

    async def guide_request_cancel(self, payload: dict):
        """{"request_id":"123"}"""
        return await self.make_request(GUIDE_REQUEST_CANCEL, payload)

    async def guide_request_create(self, payload: dict):
        """{"community_id":"1","topic":"combat","message":"Need help with dogfighting"}"""
        return await self.make_request(GUIDE_REQUEST_CREATE, payload)

    async def guide_request_decline(self, payload: dict):
        """{"request_id":"123"}"""
        return await self.make_request(GUIDE_REQUEST_DECLINE, payload)

    async def guide_request_remove(self, payload: dict):
        """{"request_id":"123"}"""
        return await self.make_request(GUIDE_REQUEST_REMOVE, payload)

    async def guide_request_remove_all(self, payload: dict):
        """{"community_id":"1"}"""
        return await self.make_request(GUIDE_REQUEST_REMOVE_ALL, payload)

    async def guide_search(self, payload: dict):
        """{"community_id":"1","topic":"combat","page":1}"""
        return await self.make_request(GUIDE_SEARCH, payload)

    async def guide_session_terminate(self, payload: dict):
        """{"session_id":"123"}"""
        return await self.make_request(GUIDE_SESSION_TERMINATE, payload)

    async def guide_topics_list(self, payload: dict):
        """{"community_id":"1"}"""
        return await self.make_request(GUIDE_TOPICS_LIST, payload)

    # ── Lobby (expanded) ──

    async def lobby_accept_invite(self, payload: dict):
        """{"lobby_id":"123"}"""
        return await self.make_request(LOBBY_ACCEPT_INVITE, payload)

    async def lobby_cancel_invite(self, payload: dict):
        """{"lobby_id":"123","member_id":"456"}"""
        return await self.make_request(LOBBY_CANCEL_INVITE, payload)

    async def lobby_close_private(self, payload: dict):
        """{"lobby_id":"123"}"""
        return await self.make_request(LOBBY_CLOSE_PRIVATE, payload)

    async def lobby_decline_invite(self, payload: dict):
        """{"lobby_id":"123"}"""
        return await self.make_request(LOBBY_DECLINE_INVITE, payload)

    async def lobby_erase(self, payload: dict):
        """{"lobby_id":"123"}"""
        return await self.make_request(LOBBY_ERASE, payload)

    async def lobby_guide_session_history(self, payload: dict):
        """{"lobby_id":"123"}"""
        return await self.make_request(LOBBY_GUIDE_SESSION_HISTORY, payload)

    async def lobby_invite(self, payload: dict):
        """{"lobby_id":"123","member_id":"456"}"""
        return await self.make_request(LOBBY_INVITE, payload)

    async def lobby_kick(self, payload: dict):
        """{"lobby_id":"123","member_id":"456"}"""
        return await self.make_request(LOBBY_KICK, payload)

    async def lobby_leave(self, payload: dict):
        """{"lobby_id":"123"}"""
        return await self.make_request(LOBBY_LEAVE, payload)

    async def lobby_list_invites(self, payload: dict):
        """{"lobby_id":"123"}"""
        return await self.make_request(LOBBY_LIST_INVITES, payload)

    async def lobby_move(self, payload: dict):
        """{"lobby_id":"123","target_group_id":"456","position":0}"""
        return await self.make_request(LOBBY_MOVE, payload)

    async def lobby_transfer_leadership(self, payload: dict):
        """{"lobby_id":"123","member_id":"456"}"""
        return await self.make_request(LOBBY_TRANSFER_LEADERSHIP, payload)

    # ── Member (expanded) ──

    async def member_spoken_languages(self, payload: dict):
        """{"member_id":"123"}"""
        return await self.make_request(MEMBER_SPOKEN_LANGUAGES, payload)

    # ── Message (expanded) ──

    async def message_erase(self, payload: dict):
        """{"message_id":"123"}"""
        return await self.make_request(MESSAGE_ERASE, payload)

    async def message_remove_media(self, payload: dict):
        """{"message_id":"123","media_id":"456"}"""
        return await self.make_request(MESSAGE_REMOVE_MEDIA, payload)

    async def message_soft_erase(self, payload: dict):
        """{"message_id":"123"}"""
        return await self.make_request(MESSAGE_SOFT_ERASE, payload)

    # ── Moderation ──

    async def moderation_kickban(self, payload: dict):
        """{"community_id":"1","member_id":"123","reason":"Violating rules","duration":86400}"""
        return await self.make_request(MODERATION_KICKBAN, payload)

    # ── Notifications ──

    async def notification_read_all(self, payload: dict):
        """{}"""
        return await self.make_request(NOTIFICATION_READ_ALL, payload)

    async def notification_read(self, payload: dict):
        """{"notification_id":"123"}"""
        return await self.make_request(NOTIFICATION_READ, payload)

    async def notification_remove_all(self, payload: dict):
        """{}"""
        return await self.make_request(NOTIFICATION_REMOVE_ALL, payload)

    async def notification_remove(self, payload: dict):
        """{"notification_id":"123"}"""
        return await self.make_request(NOTIFICATION_REMOVE, payload)

    async def notification_subscribe(self, payload: dict):
        """{"entity_type":"forum_thread","entity_id":"123"}"""
        return await self.make_request(NOTIFICATION_SUBSCRIBE, payload)

    # ── Role (expanded) ──

    async def edit_role(self, payload: dict):
        """{"role_id":"660855","name":"Edited role","description":"Updated","permissions":{...},"visible":1,"highlightable":0,"tracked":0,"color":"FF0000"}"""
        return await self.make_request(ROLE_EDIT, payload)

    async def remove_role(self, payload: dict):
        """{"role_id":"660855"}"""
        return await self.make_request(ROLE_REMOVE, payload)

    # ── Search (expanded) ──

    async def search_content_simple(self, payload: dict):
        """{"community_id":"1","text":"search query","page":1}"""
        return await self.make_request(SEARCH_CONTENT_SIMPLE, payload)

    # ── Blocklist (expanded) ──

    async def blocklist_get(self, payload: dict):
        """{}"""
        return await self.make_request(BLOCKLIST_GET, payload)

    async def blocklist_ids(self, payload: dict):
        """{}"""
        return await self.make_request(BLOCKLIST_IDS, payload)

    async def fetch_embed(self, url: str):
        """Fetch embed/media data for a URL. Returns the embed data dict."""
        return await self.make_request('/api/spectrum/media/embed/fetch', {"url": url})

    async def upload_image(self, file_path: str, filename: str = None, content_type: str = None):
        """Upload an image to Spectrum. Returns the media data dict."""
        import mimetypes
        await self._client._ready_event.wait()

        if filename is None:
            filename = os.path.basename(file_path)
        if content_type is None:
            content_type = mimetypes.guess_type(file_path)[0] or "image/png"

        headers = {**self.headers}
        if self._client_id:
            headers['x-tavern-id'] = self._client_id

        data = aiohttp.FormData()
        data.add_field('file', open(file_path, 'rb'), filename=filename, content_type=content_type)

        async with self._session.post(
                '/api/spectrum/media/upload/image',
                data=data,
                headers=headers,
                cookies=self.cookies
        ) as resp:
            response = await resp.json()
            if response is None:
                raise NullResponseError()
            elif response.get('success'):
                return response['data']
            else:
                raise exception_map.get(response.get('code', 0), HTTPError)(response.get('msg', 'Upload failed'))

    # --- V2 API Endpoints ---

    async def v2_bookmark_add(self, payload: dict):
        """{"entity_type":"lobby","entity_id":"123","folder_id":"456"}"""
        return await self.make_request(V2_BOOKMARK_ADD, payload)


    async def v2_bookmark_list(self, payload: dict):
        """{"community_id":"1"}"""
        return await self.make_request(V2_BOOKMARK_LIST, payload)


    async def v2_bookmark_move(self, payload: dict):
        """{"bookmark_id":"123","folder_id":"456"}"""
        return await self.make_request(V2_BOOKMARK_MOVE, payload)


    async def v2_bookmark_remove(self, payload: dict):
        """{"bookmark_id":"123"}"""
        return await self.make_request(V2_BOOKMARK_REMOVE, payload)


    async def v2_bookmark_rename(self, payload: dict):
        """{"bookmark_id":"123","name":"New Name"}"""
        return await self.make_request(V2_BOOKMARK_RENAME, payload)

    # ─── V2 Community methods ────────────────────────────────────────────


    async def v2_community_list(self, payload: dict):
        """{}"""
        return await self.make_request(V2_COMMUNITY_LIST, payload)


    async def v2_community_members(self, payload: dict):
        """{"community_id":"1","page":1,"pagesize":12,"sort":"displayname","sort_descending":0}"""
        return await self.make_request(V2_COMMUNITY_MEMBERS, payload)


    async def v2_community_my_roles(self, payload: dict):
        """{"community_id":"1"}"""
        return await self.make_request(V2_COMMUNITY_MY_ROLES, payload)


    async def v2_community_roles(self, payload: dict):
        """{"community_id":"1"}"""
        return await self.make_request(V2_COMMUNITY_ROLES, payload)


    async def v2_community_role_create(self, payload: dict):
        """{"community_id":"1","name":"Role Name","description":"Description","permissions":{...},"visible":1,"highlightable":0,"tracked":0,"color":"919191"}"""
        return await self.make_request(V2_COMMUNITY_ROLE_CREATE, payload)


    async def v2_community_role_edit(self, payload: dict):
        """{"role_id":"123","name":"New Name","description":"New Desc","permissions":{...},"visible":1,"highlightable":0,"tracked":0,"color":"919191"}"""
        return await self.make_request(V2_COMMUNITY_ROLE_EDIT, payload)


    async def v2_community_role_remove(self, payload: dict):
        """{"role_id":"123"}"""
        return await self.make_request(V2_COMMUNITY_ROLE_REMOVE, payload)


    async def v2_community_role_reorder(self, payload: dict):
        """{"community_id":"1","source_role_id":"123","target_role_id":"456"}"""
        return await self.make_request(V2_COMMUNITY_ROLE_REORDER, payload)


    async def v2_community_emojis(self, payload: dict):
        """{"community_id":"1"}"""
        return await self.make_request(V2_COMMUNITY_EMOJIS, payload)


    async def v2_community_emoji_create(self, payload: dict):
        """{"community_id":"1","name":"emoji_name","media_id":"123"}"""
        return await self.make_request(V2_COMMUNITY_EMOJI_CREATE, payload)


    async def v2_community_emoji_remove(self, payload: dict):
        """{"community_id":"1","emoji_id":"123"}"""
        return await self.make_request(V2_COMMUNITY_EMOJI_REMOVE, payload)


    async def v2_community_emoji_upload(self, file_path: str, community_id: str, filename: str = None, content_type: str = None):
        """Upload an emoji image via FormData. Returns the media data dict."""
        import mimetypes
        await self._client._ready_event.wait()

        if filename is None:
            filename = os.path.basename(file_path)
        if content_type is None:
            content_type = mimetypes.guess_type(file_path)[0] or "image/png"

        headers = {**self.headers}
        if self._client_id:
            headers['x-tavern-id'] = self._client_id

        data = aiohttp.FormData()
        data.add_field('file', open(file_path, 'rb'), filename=filename, content_type=content_type)
        data.add_field('community_id', community_id)

        async with self._session.post(
                V2_COMMUNITY_EMOJI_UPLOAD,
                data=data,
                headers=headers,
                cookies=self.cookies
        ) as resp:
            response = await resp.json()
            if response is None:
                raise NullResponseError()
            elif response.get('success'):
                return response['data']
            else:
                raise exception_map.get(response.get('code', 0), HTTPError)(response.get('msg', 'Emoji upload failed'))


    async def v2_community_member_profile(self, community_id: str, nickname: str):
        """Fetch a member's community profile by nickname."""
        endpoint = f"/api/spectrum/v2/community/{community_id}/member/{nickname}/profile"
        return await self.make_request(endpoint, {})

    # ─── V2 Forum methods ────────────────────────────────────────────────


    async def v2_forum_channel_list(self, payload: dict):
        """{"community_id":"1"}"""
        return await self.make_request(V2_FORUM_CHANNEL_LIST, payload)


    async def v2_forum_channel_move(self, payload: dict):
        """{"channel_id":"123","group_id":"456"}"""
        return await self.make_request(V2_FORUM_CHANNEL_MOVE, payload)


    async def v2_forum_channel_reorder(self, payload: dict):
        """{"community_id":"1","channel_id":"123","position":0}"""
        return await self.make_request(V2_FORUM_CHANNEL_REORDER, payload)


    async def v2_forum_channel_threads(self, payload: dict):
        """{"channel_id":"123","page":1,"sort":"hot","label_id":null}"""
        return await self.make_request(V2_FORUM_CHANNEL_THREADS, payload)


    async def v2_forum_channel_group_list(self, payload: dict):
        """{"community_id":"1"}"""
        return await self.make_request(V2_FORUM_CHANNEL_GROUP_LIST, payload)


    async def v2_forum_channel_group_move(self, payload: dict):
        """{"group_id":"123","position":0}"""
        return await self.make_request(V2_FORUM_CHANNEL_GROUP_MOVE, payload)


    async def v2_forum_channel_group_reorder(self, payload: dict):
        """{"community_id":"1","group_id":"123","position":0}"""
        return await self.make_request(V2_FORUM_CHANNEL_GROUP_REORDER, payload)


    async def v2_forum_thread_get(self, payload: dict):
        """{"thread_id":"123"}"""
        return await self.make_request(V2_FORUM_THREAD_GET, payload)

    # ─── V2 Game methods ─────────────────────────────────────────────────


    async def v2_game_party(self, payload: dict):
        """{}"""
        return await self.make_request(V2_GAME_PARTY, payload)

    # ─── V2 Identity methods ─────────────────────────────────────────────


    async def v2_get_identity_infos(self, payload: dict):
        """{"member_ids":["123","456"]}"""
        return await self.make_request(V2_GET_IDENTITY_INFOS, payload)

    # ─── V2 Guide methods ────────────────────────────────────────────────


    async def v2_guide_me(self, payload: dict):
        """{}"""
        return await self.make_request(V2_GUIDE_ME, payload)


    async def v2_guide_register(self, payload: dict):
        """{"topics":["topic1"],"languages":["en"],"description":"Guide description"}"""
        return await self.make_request(V2_GUIDE_REGISTER, payload)


    async def v2_guide_deregister(self, payload: dict):
        """{}"""
        return await self.make_request(V2_GUIDE_DEREGISTER, payload)


    async def v2_guide_profile_update(self, payload: dict):
        """{"topics":["topic1"],"languages":["en"],"description":"Updated description"}"""
        return await self.make_request(V2_GUIDE_PROFILE_UPDATE, payload)


    async def v2_guide_registration_criteria_check(self, payload: dict):
        """{}"""
        return await self.make_request(V2_GUIDE_REGISTRATION_CRITERIA_CHECK, payload)


    async def v2_guide_request_create(self, payload: dict):
        """{"topic":"topic1","language":"en","description":"Need help with..."}"""
        return await self.make_request(V2_GUIDE_REQUEST_CREATE, payload)


    async def v2_guide_request_incoming(self, payload: dict):
        """{}"""
        return await self.make_request(V2_GUIDE_REQUEST_INCOMING, payload)


    async def v2_guide_request_outgoing(self, payload: dict):
        """{}"""
        return await self.make_request(V2_GUIDE_REQUEST_OUTGOING, payload)


    async def v2_guide_request_remove_all(self, payload: dict):
        """{}"""
        return await self.make_request(V2_GUIDE_REQUEST_REMOVE_ALL, payload)


    async def v2_guide_request_accept(self, request_id: str):
        """Accept a guide request by ID."""
        endpoint = f"/api/spectrum/v2/guide/request/{request_id}/accept"
        return await self.make_request(endpoint, {})


    async def v2_guide_request_cancel(self, request_id: str):
        """Cancel a guide request by ID."""
        endpoint = f"/api/spectrum/v2/guide/request/{request_id}/cancel"
        return await self.make_request(endpoint, {})


    async def v2_guide_request_decline(self, request_id: str):
        """Decline a guide request by ID."""
        endpoint = f"/api/spectrum/v2/guide/request/{request_id}/decline"
        return await self.make_request(endpoint, {})


    async def v2_guide_request_remove(self, request_id: str):
        """Remove a guide request by ID."""
        endpoint = f"/api/spectrum/v2/guide/request/{request_id}/remove"
        return await self.make_request(endpoint, {})


    async def v2_guide_search(self, payload: dict):
        """{"topic":"topic1","language":"en","page":1}"""
        return await self.make_request(V2_GUIDE_SEARCH, payload)


    async def v2_guide_session_active(self, payload: dict):
        """{}"""
        return await self.make_request(V2_GUIDE_SESSION_ACTIVE, payload)


    async def v2_guide_session_endorse(self, session_id: str):
        """Endorse a guide after a session."""
        endpoint = f"/api/spectrum/v2/guide/session/{session_id}/endorse"
        return await self.make_request(endpoint, {})


    async def v2_guide_session_endorse_decline(self, session_id: str):
        """Decline to endorse a guide after a session."""
        endpoint = f"/api/spectrum/v2/guide/session/{session_id}/endorse/decline"
        return await self.make_request(endpoint, {})


    async def v2_guide_session_terminate(self, session_id: str):
        """Terminate an active guide session."""
        endpoint = f"/api/spectrum/v2/guide/session/{session_id}/terminate"
        return await self.make_request(endpoint, {})


    async def v2_guide_stats(self, payload: dict):
        """{}"""
        return await self.make_request(V2_GUIDE_STATS, payload)


    async def v2_guide_topic_list(self, payload: dict):
        """{}"""
        return await self.make_request(V2_GUIDE_TOPIC_LIST, payload)

    # ─── V2 Lobby methods ────────────────────────────────────────────────


    async def v2_lobby_public_list(self, payload: dict):
        """{"community_id":"1"}"""
        return await self.make_request(V2_LOBBY_PUBLIC_LIST, payload)


    async def v2_lobby_public_move(self, payload: dict):
        """{"lobby_id":"123","position":0}"""
        return await self.make_request(V2_LOBBY_PUBLIC_MOVE, payload)


    async def v2_lobby_public_reorder(self, payload: dict):
        """{"community_id":"1","lobby_id":"123","position":0}"""
        return await self.make_request(V2_LOBBY_PUBLIC_REORDER, payload)


    async def v2_lobby_group_list(self, payload: dict):
        """{}"""
        return await self.make_request(V2_LOBBY_GROUP_LIST, payload)


    async def v2_lobby_private_list(self, payload: dict):
        """{}"""
        return await self.make_request(V2_LOBBY_PRIVATE_LIST, payload)


    async def v2_lobby_private_close(self, payload: dict):
        """{"lobby_id":"123"}"""
        return await self.make_request(V2_LOBBY_PRIVATE_CLOSE, payload)


    async def v2_lobby_private_open(self, payload: dict):
        """{"member_ids":["123","456"]}"""
        return await self.make_request(V2_LOBBY_PRIVATE_OPEN, payload)


    async def v2_lobby_chats_list(self, payload: dict):
        """{"page":1,"pagesize":20}"""
        return await self.make_request(V2_LOBBY_CHATS_LIST, payload)


    async def v2_lobby_chats_search(self, payload: dict):
        """{"text":"search term","page":1}"""
        return await self.make_request(V2_LOBBY_CHATS_SEARCH, payload)

    # ─── V2 Member methods ───────────────────────────────────────────────


    async def v2_member_profile(self, payload: dict):
        """{"member_id":"123"}"""
        return await self.make_request(V2_MEMBER_PROFILE, payload)


    async def v2_member_role_add(self, payload: dict):
        """{"member_id":"123","role_id":"456"}"""
        return await self.make_request(V2_MEMBER_ROLE_ADD, payload)


    async def v2_member_role_remove(self, payload: dict):
        """{"member_id":"123","role_id":"456"}"""
        return await self.make_request(V2_MEMBER_ROLE_REMOVE, payload)


    async def v2_member_role_set(self, payload: dict):
        """{"member_id":"123","role_ids":["456","789"]}"""
        return await self.make_request(V2_MEMBER_ROLE_SET, payload)


    async def v2_member_settings(self, payload: dict):
        """{}"""
        return await self.make_request(V2_MEMBER_SETTINGS, payload)


    async def v2_member_settings_save(self, payload: dict):
        """{"settings":{"notification_email":true,"notification_push":true}}"""
        return await self.make_request(V2_MEMBER_SETTINGS_SAVE, payload)

    # ─── V2 Message methods ──────────────────────────────────────────────


    async def v2_message_send(self, payload: dict):
        """{"lobby_id":"123","content_blocks":[...],"plaintext":"Hello"}"""
        return await self.make_request(V2_MESSAGE_SEND, payload)

    # ─── V2 Moderation methods ───────────────────────────────────────────


    async def v2_moderation_kickban(self, payload: dict):
        """{"community_id":"1","member_id":"123","action":"kick","reason":"Rule violation","duration":null}"""
        return await self.make_request(V2_MODERATION_KICKBAN, payload)

    # ─── V2 Search methods ───────────────────────────────────────────────


    async def v2_search_member_mapping(self, payload: dict):
        """{"community_id":"1","text":"username","page":1}"""
        return await self.make_request(V2_SEARCH_MEMBER_MAPPING, payload)

    # ─── End V2 methods ──────────────────────────────────────────────────



    async def make_request(self, endpoint: str, payload: dict):
        await self._client._ready_event.wait()
        log.debug("Sending request to %s with payload %s" % (endpoint, payload))
        headers = {
            **self.headers,
            'X-Tavern-action-id': '1',
        }

        if self._client_id:
            headers['x-tavern-id'] = self._client_id

        for attempt in range(self.MAX_RETRIES):
            async with self._session.post(
                    endpoint,
                    json=payload,
                    headers=headers,
                    cookies=self.cookies
            ) as resp:
                if resp.status == 429:
                    retry_after = float(resp.headers.get('Retry-After', self.RETRY_BACKOFF * (2 ** attempt)))
                    log.warning("Rate limited on %s, retrying after %.1fs", endpoint, retry_after)
                    await asyncio.sleep(retry_after)
                    continue

                if resp.status >= 500 and attempt < self.MAX_RETRIES - 1:
                    wait = self.RETRY_BACKOFF * (2 ** attempt)
                    log.warning("Server error %d on %s, retrying after %.1fs", resp.status, endpoint, wait)
                    await asyncio.sleep(wait)
                    continue

                content_type = resp.headers.get('Content-Type', '')
                if 'application/json' not in content_type:
                    raise HTTPError(f"Unexpected response type '{content_type}' from {endpoint} (status {resp.status})")

                response = await resp.json()
                if response is None:
                    raise NullResponseError()
                elif response.get('success'):
                    return response['data']
                else:
                    log.error("Made bad request: %s", payload)
                    raise exception_map.get(response['code'], HTTPError)(response['msg'])

        raise HTTPError(f"Max retries exceeded for {endpoint}")

    async def identify(self):
        log.info("Identifying")
        async with aiohttp.ClientSession() as session:
            async with session.post(
                    IDENTIFY_URL,
                    cookies=self.cookies,
                    headers=self.headers,
                    json={},
                    timeout=30
            ) as resp:
                body = await resp.json()
                if not body["success"]:
                    raise InvalidTokenException("An invalid token has been passed")

        token = body.get("data", {}).get("token")
        identify_callback = self._client._get_event_callback("identify")
        await identify_callback(body.get("data", {}))

        if token:
            self._gateway_token = token
            parts = base64.urlsafe_b64decode(token.split(".")[1] + "==").decode("utf-8")
            token_payload = json.loads(parts)
            self._client_id = token_payload['client_id']
            log.info("Successfully identified with member_id: %s", token_payload['member_id'])
        else:
            log.info("Connecting without identification")

        return self._gateway_token
