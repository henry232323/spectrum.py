import aiohttp

CREATE_MESSAGE_ENDPOINT = "https://robertsspaceindustries.com/api/spectrum/message/create"


class HTTP:
    def __init__(self, gateway, token):
        self._gateway = gateway
        self._token = token

    async def send_message(self, payload: str):
        async with aiohttp.ClientSession() as session:
            async with session.post(CREATE_MESSAGE_ENDPOINT, json=payload, headers={
                **self._gateway.headers,
                'X-Tavern-action-id': '1',
                'x-tavern-id': self._gateway._client_id
            },
                                    cookies=self._gateway.cookies) as resp:
                return await resp.json()
