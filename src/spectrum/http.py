import asyncio

import aiohttp

CREATE_MESSAGE_ENDPOINT = "https://robertsspaceindustries.com/api/spectrum/message/create"
FETCH_PRESENCES_ENDPOINT = "https://robertsspaceindustries.com/api/spectrum/lobby/presences"
FETCH_THREAD = "https://robertsspaceindustries.com/api/spectrum/forum/thread/nested"


class HTTP:
    def __init__(self, gateway, token):
        self._gateway = gateway
        self._token = token

        loop = asyncio.get_event_loop()
        self._session = aiohttp.ClientSession(loop=loop)

    async def send_message(self, payload: str):
        return await self.make_request(CREATE_MESSAGE_ENDPOINT, payload)

    async def fetch_presences(self, payload):
        return await self.make_request(FETCH_PRESENCES_ENDPOINT, payload)

    async def fetch_thread(self, payload):
        return await self.make_request(FETCH_THREAD, payload)

    async def make_request(self, endpoint, payload):
        await self._gateway._client._ready_event.wait()

        async with self._session.post(
                endpoint,
                json=payload,
                headers={
                    **self._gateway.headers,
                    'X-Tavern-action-id': '1',
                    'x-tavern-id': self._gateway._client_id
                },
                cookies=self._gateway.cookies
        ) as resp:
            return await resp.json()
