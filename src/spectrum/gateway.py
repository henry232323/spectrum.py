import asyncio
import json
import logging
import traceback

import aiohttp
import yarl

from . import httpclient


class WebSocketClosure(Exception):
    pass


class ReconnectWebSocket(Exception):
    pass


log = logging.getLogger(__name__)


class Gateway:
    DEFAULT_GATEWAY = yarl.URL('wss://robertsspaceindustries.com/ws/spectrum')
    _max_heartbeat_timeout = 360
    _max_backoff = 60

    def __init__(self, *, client: 'httpclient.HTTPClient', rsi_token: str, device_id: str):
        self._rsi_token = rsi_token
        self._device_id = device_id
        self._client = client
        self._ws_token = None
        self._ws_url = None
        self.socket = None
        self._running = False

    async def subscribe_to_key(self, *keys: str, scope=None):
        payload = {
            "type": "subscribe",
            "subscription_keys": [
                *keys
            ],
            "subscription_scope": scope
        }
        log.debug("Sent payload: %s", payload)
        await self.socket.send_json(payload)

    async def send_event(self, event_type: str, data: dict):
        """Send a generic event over the WebSocket (e.g. typing indicators).

        Parameters
        ----------
        event_type : str
            The event type string, e.g. ``"message_lobby.typing.start"``.
        data : dict
            Additional payload fields merged into the sent message.
        """
        payload = {"type": event_type, **data}
        log.debug("Sent event: %s", payload)
        await self.socket.send_json(payload)

    async def start(self, token=None):
        log.info('Starting gateway')
        self._running = True

        if token:
            self._ws_token = token
            self._ws_url = self.DEFAULT_GATEWAY.with_query(token=self._ws_token)
        else:
            self._ws_url = str(Gateway.DEFAULT_GATEWAY)

        arguments = {
            'max_msg_size': 0,
            'timeout': 30.0,
            'autoclose': False,
            'headers': {
                'x-rsi-token': self._rsi_token or ""
            },
        }

        first_connect = True
        backoff = 1
        while self._running:
            async with aiohttp.ClientSession() as session:
                try:
                    if not first_connect:
                        self._client._ready_event.clear()
                        new_token = await self._client._http.identify()
                        if new_token:
                            self._ws_token = new_token
                            self._ws_url = self.DEFAULT_GATEWAY.with_query(token=self._ws_token)
                    first_connect = False

                    self.socket = await session.ws_connect(str(self._ws_url), **arguments)
                    backoff = 1

                    while True:
                        await self.poll_event()
                except ReconnectWebSocket:
                    log.info("Websocket closed, reconnecting")
                    if self.socket:
                        await self.socket.close()

                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, self._max_backoff)

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
                log.debug('Received %s', msg)
                raise msg.data
            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSING, aiohttp.WSMsgType.CLOSE):
                log.debug('Received %s', msg)
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
            log.debug('Received %s', payload)
            await self._client._dispatch_event(payload['type'], payload)

    def close(self):
        self._running = False
