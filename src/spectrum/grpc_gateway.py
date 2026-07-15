"""
ConnectRPC/gRPC push client for Spectrum.

This module provides an alternative to the WebSocket gateway using the
ConnectRPC bidi-streaming endpoint at:
    https://robertsspaceindustries.com/grpc/spectrum/ws

Protocol details (best-effort, pending .proto capture):
- Transport: HTTP/2-style streaming over HTTPS (ConnectRPC with protobuf binary)
- Client sends: Subscription messages (subscribe/unsubscribe), KeepAlive pings
- Server streams: Events matching subscribed topics (same event types as WebSocket)
- Auth: Authorization: Bearer <token> header

Since we do not have the .proto definitions, this implementation uses a
JSON-framed fallback approach via ConnectRPC's JSON encoding option. The
connect-es protocol supports both binary protobuf and JSON encodings; we
attempt JSON first which is more inspectable without proto definitions.

TODO: Once .proto files are captured from traffic, replace the JSON framing
with proper protobuf serialization using grpcio or betterproto.
"""

from __future__ import annotations

import asyncio
import json
import logging
import struct
import traceback
from typing import TYPE_CHECKING

import aiohttp
import yarl

if TYPE_CHECKING:
    from . import httpclient

log = logging.getLogger(__name__)


class GRPCGatewayError(Exception):
    """Raised when the gRPC gateway encounters an error."""
    pass


class GRPCReconnect(Exception):
    """Signal to reconnect the gRPC stream."""
    pass


class GRPCGateway:
    """
    ConnectRPC streaming client for Spectrum push events.

    Drop-in alternative to the WebSocket Gateway class. Uses the same
    interface: start(token), subscribe_to_key(*keys, scope), close().

    Events are dispatched through self._client._dispatch_event(type, payload),
    identical to the WebSocket gateway.
    """

    DEFAULT_GATEWAY = yarl.URL('https://robertsspaceindustries.com/grpc/spectrum/ws')

    # ConnectRPC streaming endpoint paths (to be confirmed via traffic capture)
    # The bidi stream is typically accessed via POST with streaming content-type
    STREAM_PATH = '/grpc/spectrum/ws/PushService/Stream'

    _max_heartbeat_timeout = 360
    _max_backoff = 60
    _keepalive_interval = 30  # seconds between keepalive pings

    def __init__(self, *, client: 'httpclient.HTTPClient', rsi_token: str, device_id: str):
        self._rsi_token = rsi_token
        self._device_id = device_id
        self._client = client
        self._token: str | None = None
        self._running = False
        self._session: aiohttp.ClientSession | None = None
        self._response: aiohttp.ClientResponse | None = None
        self._keepalive_task: asyncio.Task | None = None
        self._subscribed_keys: list[str] = []

    async def subscribe_to_key(self, *keys: str, scope=None):
        """Subscribe to one or more topic keys.

        Mirrors the WebSocket gateway interface. Sends a subscription message
        over the gRPC stream.

        If the stream is not yet connected, the keys are queued and will be
        sent once the connection is established.
        """
        payload = {
            "type": "subscribe",
            "subscription_keys": list(keys),
            "subscription_scope": scope,
        }
        log.debug("gRPC subscribe payload: %s", payload)

        # Track subscriptions for reconnect
        for key in keys:
            if key not in self._subscribed_keys:
                self._subscribed_keys.append(key)

        if self._session and not self._session.closed:
            await self._send_message(payload)

    async def _send_message(self, payload: dict):
        """Send a JSON message over the streaming connection.

        ConnectRPC supports a JSON encoding mode. We frame each message
        as a length-prefixed JSON payload following the Connect streaming
        wire format:

            [flags: 1 byte][length: 4 bytes big-endian][message: N bytes]

        For JSON encoding, flags = 0x00 for data frames.

        TODO: Replace with proper protobuf serialization once .proto is available.
        """
        # For now, we attempt to use the server-sent events or chunked
        # streaming approach that ConnectRPC supports for unary/stream RPCs
        # over HTTP/1.1. The exact framing will depend on traffic capture.
        #
        # Placeholder: store pending messages to send when stream is writable
        log.debug("gRPC send: %s", payload)
        self._pending_sends.append(payload)

    async def start(self, token=None):
        """Start the gRPC streaming connection.

        Args:
            token: The authentication token from identify/getIdentityInfos.
                   Used as Bearer token in Authorization header.
        """
        log.info('Starting gRPC gateway')
        self._running = True
        self._pending_sends: list[dict] = []

        if token:
            self._token = token

        first_connect = True
        backoff = 1

        while self._running:
            try:
                if not first_connect:
                    self._client._ready_event.clear()
                    new_token = await self._client._http.identify()
                    if new_token:
                        self._token = new_token
                first_connect = False

                await self._connect_stream()
                backoff = 1

            except GRPCReconnect:
                log.info("gRPC stream closed, reconnecting")
            except Exception as e:
                log.error("gRPC gateway error: %s", traceback.format_exc())

            if self._keepalive_task and not self._keepalive_task.done():
                self._keepalive_task.cancel()

            if self._session and not self._session.closed:
                await self._session.close()
                self._session = None

            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, self._max_backoff)

    async def _connect_stream(self):
        """Establish the streaming connection to the ConnectRPC endpoint.

        ConnectRPC bidi streaming over HTTP/2 uses a POST request with:
        - Content-Type: application/connect+proto (or application/connect+json)
        - Connect-Protocol-Version: 1
        - The request body is a stream of framed messages
        - The response body is a stream of framed messages

        For HTTP/1.1 fallback (which aiohttp uses), ConnectRPC falls back to
        server-sent events or chunked transfer encoding for server streams.

        TODO: The exact content-type and framing needs to be confirmed via
        traffic capture. This implementation tries the JSON encoding variant.
        """
        headers = {
            'Content-Type': 'application/connect+json',
            'Connect-Protocol-Version': '1',
            'x-rsi-token': self._rsi_token or '',
        }

        if self._token:
            headers['Authorization'] = f'Bearer {self._token}'

        if self._device_id:
            headers['x-rsi-device'] = self._device_id

        self._session = aiohttp.ClientSession()

        # ConnectRPC server-stream: POST with the initial request payload,
        # server responds with a stream of framed messages.
        #
        # For bidi-stream over HTTP/1.1, some implementations use WebSocket
        # upgrade or a pair of half-duplex streams. We attempt the streaming
        # POST approach first.
        #
        # The initial message might need to contain auth/subscription info.
        initial_payload = self._build_connect_request()

        try:
            self._response = await self._session.post(
                str(self.DEFAULT_GATEWAY) if not self.STREAM_PATH else
                f'https://robertsspaceindustries.com{self.STREAM_PATH}',
                headers=headers,
                data=self._encode_connect_frame(initial_payload),
                timeout=aiohttp.ClientTimeout(
                    total=None,  # No total timeout for streaming
                    sock_read=self._max_heartbeat_timeout,
                ),
            )

            if self._response.status != 200:
                body = await self._response.text()
                log.error("gRPC connect failed: status=%d body=%s",
                          self._response.status, body[:500])
                raise GRPCGatewayError(
                    f"Connect failed with status {self._response.status}")

            # Start keepalive
            self._keepalive_task = asyncio.create_task(self._keepalive_loop())

            # Re-subscribe to all previously subscribed keys
            if self._subscribed_keys:
                await self._send_message({
                    "type": "subscribe",
                    "subscription_keys": self._subscribed_keys,
                    "subscription_scope": None,
                })

            # Read the stream
            await self._read_stream()

        finally:
            if self._response:
                self._response.close()
                self._response = None

    def _build_connect_request(self) -> dict:
        """Build the initial ConnectRPC request payload.

        TODO: This needs to be replaced with the actual protobuf message
        structure once we have the .proto definitions. For now, we send
        a JSON object that mirrors what we know the WebSocket sends.
        """
        return {
            "type": "connect",
            "token": self._token,
            "device_id": self._device_id,
        }

    def _encode_connect_frame(self, payload: dict) -> bytes:
        """Encode a message in ConnectRPC streaming wire format.

        Connect streaming wire format (for each message):
            [flags: 1 byte][length: 4 bytes big-endian][message: N bytes]

        Flags:
            0x00 = normal data frame
            0x01 = trailer frame (end of stream)

        For JSON encoding, the message is UTF-8 JSON bytes.

        TODO: Replace with protobuf serialization once .proto is available.
        """
        message_bytes = json.dumps(payload).encode('utf-8')
        flags = 0x00
        length = len(message_bytes)
        header = struct.pack('>BI', flags, length)
        return header + message_bytes

    def _decode_connect_frame(self, data: bytes) -> tuple[int, dict, int]:
        """Decode a ConnectRPC streaming frame.

        Returns:
            Tuple of (flags, parsed_payload, total_bytes_consumed)

        Raises:
            ValueError if the frame is incomplete or malformed.
        """
        if len(data) < 5:
            raise ValueError("Incomplete frame header")

        flags, length = struct.unpack('>BI', data[:5])
        if len(data) < 5 + length:
            raise ValueError("Incomplete frame body")

        message_bytes = data[5:5 + length]

        try:
            payload = json.loads(message_bytes.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Might be binary protobuf - log and skip
            log.warning("Could not decode frame as JSON (may be protobuf): %s",
                        message_bytes[:100])
            payload = {"_raw": message_bytes.hex(), "type": "unknown"}

        return flags, payload, 5 + length

    async def _read_stream(self):
        """Read and process the response stream from the ConnectRPC endpoint.

        The response is a chunked stream of ConnectRPC framed messages.
        Each frame contains an event payload similar to the WebSocket events.
        """
        buffer = bytearray()

        async for chunk in self._response.content.iter_any():
            if not self._running:
                break

            buffer.extend(chunk)

            # Process all complete frames in the buffer
            while len(buffer) >= 5:
                try:
                    flags, payload, consumed = self._decode_connect_frame(
                        bytes(buffer))
                except ValueError:
                    # Incomplete frame, wait for more data
                    break

                buffer = buffer[consumed:]

                if flags == 0x01:
                    # Trailer frame - end of stream
                    log.info("Received end-of-stream trailer")
                    raise GRPCReconnect()

                # Process the event
                await self._handle_event(payload)

        # Stream ended
        if self._running:
            raise GRPCReconnect()

    async def _handle_event(self, payload: dict):
        """Handle an incoming event from the gRPC stream.

        Events have the same structure as WebSocket events:
        {"type": "...", ...data...}
        """
        if not isinstance(payload, dict):
            log.warning("Received non-dict payload: %s", payload)
            return

        event_type = payload.get('type')
        if not event_type:
            log.debug("Received payload without type: %s", payload)
            return

        # Keepalive/heartbeat acknowledgements
        if event_type in ('pong', 'keepalive', 'heartbeat'):
            log.debug("Received keepalive response")
            return

        log.debug('gRPC received: %s', payload)
        await self._client._dispatch_event(event_type, payload)

    async def _keepalive_loop(self):
        """Periodically send keepalive pings to maintain the connection."""
        try:
            while self._running:
                await asyncio.sleep(self._keepalive_interval)
                if self._running:
                    await self._send_message({
                        "type": "keepalive",
                    })
        except asyncio.CancelledError:
            pass

    def close(self):
        """Stop the gRPC gateway. Mirrors the WebSocket Gateway.close() interface."""
        self._running = False
        if self._keepalive_task and not self._keepalive_task.done():
            self._keepalive_task.cancel()
