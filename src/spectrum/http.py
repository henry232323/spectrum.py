import asyncio

import aiohttp

SPECTRUM_API_BASE = "https://robertsspaceindustries.com/api/spectrum/"
CREATE_MESSAGE_ENDPOINT = "https://robertsspaceindustries.com/api/spectrum/message/create"
FETCH_PRESENCES_ENDPOINT = "https://robertsspaceindustries.com/api/spectrum/lobby/presences"
FETCH_THREAD = "https://robertsspaceindustries.com/api/spectrum/forum/thread/nested"
FETCH_HISTORY = "https://robertsspaceindustries.com/api/spectrum/message/history"
FETCH_MEMBER_BY_ID = "https://robertsspaceindustries.com/api/spectrum/member/info/id"
FETCH_MEMBER_BY_HANDLE = "https://robertsspaceindustries.com/api/spectrum/member/info/nickname"
FETCH_MEMBER_ROLES = "https://robertsspaceindustries.com/api/spectrum/member/roles"
FETCH_MEMBER_COUNTERS = "https://robertsspaceindustries.com/api/spectrum/member/counters"


class HTTP:
    def __init__(self, gateway, token):
        self._gateway = gateway
        self._token = token

        loop = asyncio.get_event_loop()
        self._session = aiohttp.ClientSession(loop=loop)

    async def send_message(self, payload: dict):
        return await self.make_request(CREATE_MESSAGE_ENDPOINT, payload)

    async def fetch_presences(self, payload):
        return await self.make_request(FETCH_PRESENCES_ENDPOINT, payload)

    async def fetch_thread(self, payload):
        return await self.make_request(FETCH_THREAD, payload)

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

    async def make_request(self, endpoint, payload):
        await self._gateway._client._ready_event.wait()
        headers = {
            **self._gateway.headers,
            'X-Tavern-action-id': '1',
        }

        if self._gateway._client_id:
            headers['x-tavern-id'] = self._gateway._client_id

        async with self._session.post(
                endpoint,
                json=payload,
                headers=headers,
                cookies=self._gateway.cookies
        ) as resp:
            return await resp.json()
