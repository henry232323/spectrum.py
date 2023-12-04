import asyncio
import base64
import json
import logging
import traceback

import aiohttp
import yarl

from . import client
from .models.lobby import Lobby


class WebSocketClosure(Exception):
    pass


class ReconnectWebSocket(Exception):
    pass


class InvalidTokenException(Exception):
    pass

log = logging.getLogger(__name__)

class Gateway:
    """
    {"type":"message_lobby.presence.join","lobby_id":1,"member_id":553370,"member":{"nickname":"Driver15","displayname":"Driver","avatar":"https:\/\/robertsspaceindustries.com\/media\/g6zrerb088186r\/heap_infobox\/Screenshot_5.png?v=1576397158","signature":"","meta":{"badges":[{"name":"Mercenary","icon":"https:\/\/robertsspaceindustries.com\/media\/kji9vcgdoaiibr\/heap_note\/Mercenary.png"}]},"roles":{"1":["11","12","4"]},"presence":{"status":"online","info":null,"since":1679607363}}}
    """

    IDENTIFY_URL = yarl.URL("https://robertsspaceindustries.com/api/spectrum/auth/identify")
    DEFAULT_GATEWAY = yarl.URL('wss://robertsspaceindustries.com/ws/spectrum')
    _max_heartbeat_timeout = 360

    def __init__(self, *, client: 'client.Client', token: str, device_id: str):
        self._token = token
        self._device_id = device_id
        self._client = client
        self._ws_token = None
        self._ws_url = None
        self._client_id = None
        self.socket = None
        self._running = False

        self.cookies = {
            '_rsi_device': self._device_id or "",
            'Rsi-Token': self._token or "",
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

        if self._token:
            self.headers['X-Rsi-Token'] = self._token

    async def identify(self):
        log.info("Identifying")
        async with aiohttp.ClientSession() as session:
            async with session.post(
                    self.IDENTIFY_URL,
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
        communities = body.get("data", {}).get("communities", [])
        group_lobbies = body.get("data", {}).get("group_lobbies", [])
        private_lobbies = body.get("data", {}).get("private_lobbies", [])

        if token:
            log.info("Successfully identified")
            self._ws_url = Gateway.DEFAULT_GATEWAY.with_query(token=token)
            parts = base64.b64decode(token.split(".")[1] + "==", validate=False).decode("utf-8")
            token_payload = json.loads(parts)
            self._client_id = token_payload['client_id']
        else:
            log.info("Connecting without identification")
            self._ws_url = str(Gateway.DEFAULT_GATEWAY)

        for community in communities or []:
            self._client._replace_community(community)

        tasks = []
        for lpayload in group_lobbies or []:
            lobby = self._client._replace_lobby(lpayload)
            tasks.append(self.subscribe_to_lobby(lobby))

        for lpayload in private_lobbies or []:
            lobby = self._client._replace_lobby(lpayload)
            tasks.append(self.subscribe_to_lobby(lobby))

        main_community = self._client.get_community("1")
        if main_community:
            for lobby in main_community.lobbies:
                tasks.append(self.subscribe_to_lobby(lobby))

        asyncio.create_task(self.ready_tasks(tasks))

        log.info("Finished identifying")

    async def ready_tasks(self, tasks):
        await self._client._ready_event.wait()
        for task in tasks:
            asyncio.create_task(task)

    async def register_lobby(self, lpayload):
        lobby = self._client._replace_lobby(lpayload)
        await self.subscribe_to_lobby(lobby)

    async def subscribe_to_key(self, *keys: str):
        await self.socket.send_json(
            {
                "type": "subscribe",
                "subscription_keys": [
                    *keys
                ],
                "subscription_scope": "content"
            }
        )

    async def subscribe_to_lobby(self, lobby: Lobby):
        await self.subscribe_to_key(lobby.subscription_key)

    async def start(self):
        self._running = True
        await self.identify()

        arguments = {
            'max_msg_size': 0,
            'timeout': 30.0,
            'autoclose': False,
            'headers': {
                'x-rsi-token': self._token or ""
            },
        }

        backoff = 1
        while self._running:
            async with aiohttp.ClientSession() as session:
                try:
                    self.socket = await session.ws_connect(str(self._ws_url), **arguments)

                    while True:
                        await self.poll_event()
                except ReconnectWebSocket:
                    log.info("Websocket closed, reconnecting")
                    await self.socket.close()

                await asyncio.sleep(backoff)
                backoff *= 2

    async def poll_event(self) -> None:
        """Polls for a DISPATCH event and handles the general gateway loop.
        Raises
        ------
        ConnectionClosed
            The websocket connection was terminated for unhandled reasons.
        """
        try:
            msg = await self.socket.receive(timeout=self._max_heartbeat_timeout)
            if msg.type is aiohttp.WSMsgType.TEXT:
                await self.received_message(msg.data)
            elif msg.type is aiohttp.WSMsgType.BINARY:
                await self.received_message(msg.data)
            elif msg.type is aiohttp.WSMsgType.ERROR:
                # _log.debug('Received %s', msg)
                raise msg.data
            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSING, aiohttp.WSMsgType.CLOSE):
                # _log.debug('Received %s', msg)
                raise WebSocketClosure
        except (asyncio.TimeoutError, WebSocketClosure) as e:
            traceback.print_exc()
            raise ReconnectWebSocket()

    # Ensure the keep alive handler is closed
    # if self._keep_alive:
    #     self._keep_alive.stop()
    #     self._keep_alive = None

    # if isinstance(e, asyncio.TimeoutError):
    #     _log.debug('Timed out receiving packet. Attempting a reconnect.')
    #     raise ReconnectWebSocket(self.shard_id) from None

    # code = self._close_code or self.socket.close_code
    # if self._can_handle_close():
    #     _log.debug('Websocket closed with %s, attempting a reconnect.', code)
    #     raise ReconnectWebSocket(self.shard_id) from None
    # else:
    #     _log.debug('Websocket closed with %s, cannot reconnect.', code)
    #     raise ConnectionClosed(self.socket, shard_id=self.shard_id, code=code) from None

    async def received_message(self, data):
        payload = json.loads(data)
        if isinstance(payload, dict):
            await self._client._dispatch_event(payload['type'], payload)
