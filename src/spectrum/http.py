import asyncio
import base64
import json
import logging

import aiohttp
import yarl

from spectrum.errors import HTTPError, exception_map

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


class InvalidTokenException(Exception):
    pass


log = logging.getLogger(__name__)


class HTTP:
    def __init__(self, client, rsi_token, device_id):
        self._client = client
        self._rsi_token = rsi_token
        self._gateway_token = None
        self._device_id = device_id
        self._client_id = None

        loop = asyncio.get_event_loop()
        self._session = aiohttp.ClientSession(loop=loop, base_url=SPECTRUM_API_BASE)

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
        return await self.make_request(CREATE_THREAD, payload)

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

    async def fetch_lobby_info(self, payload):
        """
        {"member_id":"3100861"}
        """
        return await self.make_request(FETCH_LOBBY_INFO, payload)

    async def make_request(self, endpoint: str, payload: dict):
        await self._client._ready_event.wait()
        headers = {
            **self.headers,
            'X-Tavern-action-id': '1',
        }

        if self._client_id:
            headers['x-tavern-id'] = self._client_id

        async with self._session.post(
                endpoint,
                json=payload,
                headers=headers,
                cookies=self.cookies
        ) as resp:
            response = await resp.json()
            if response.get('success'):
                return response['data']
            else:
                raise exception_map.get(response['code'], HTTPError)(response['msg'])

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
            parts = base64.b64decode(token.split(".")[1] + "==", validate=False).decode("utf-8")
            token_payload = json.loads(parts)
            self._client_id = token_payload['client_id']
            log.info("Successfully identified with member_id: %s", token_payload['member_id'])
        else:
            log.info("Connecting without identification")

        return self._gateway_token
