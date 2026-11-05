"""Fixtures are redacted, match the spec, and parse through the current models."""
import asyncio
import json

import pytest

import redact
import speclib
from spectrum import Client, HTTPClient
from spectrum.models import Lobby, Member, Message
from spectrum.models.thread import Thread, ThreadStub

SPEC = speclib.load_spectrum_spec()
HTTP_FIXTURES = list(speclib.http_fixtures())
WS_FIXTURES = list(speclib.ws_fixtures())


def load(path):
    return json.loads(path.read_text())


def fid(path):
    return f"{path.parent.name}/{path.stem}"


def test_there_are_fixtures():
    assert len(HTTP_FIXTURES) >= 5
    assert len(WS_FIXTURES) >= 5


@pytest.mark.parametrize("path", HTTP_FIXTURES + WS_FIXTURES, ids=fid)
def test_fixture_is_redacted(path):
    assert redact.find_leaks(load(path)) == []


@pytest.mark.parametrize("path", HTTP_FIXTURES, ids=fid)
def test_http_fixture_matches_operation_schema(path):
    fx = load(path)
    assert fx["operationId"] == path.parent.name
    op = SPEC.operation(fx["operationId"])
    status = "200" if fx["status"] == 200 and fx["response"].get("success") else "default"
    errors = sorted(op.response_validator(status).iter_errors(fx["response"]), key=lambda e: e.path)
    assert not errors, "\n".join(f"{list(e.absolute_path)}: {e.message}" for e in errors[:10])
    req_schema = op.request_schema()
    if req_schema is not None:
        req_errors = list(speclib.validator_for(req_schema, op.file).iter_errors(fx["request"]))
        assert not req_errors, [e.message for e in req_errors]


def test_verified_operations_have_a_recorded_fixture():
    recorded = {load(p)["operationId"] for p in HTTP_FIXTURES if load(p)["source"] == "recorded"}
    verified = {op.operation_id for op in SPEC.operations.values() if op.x.get("verified")}
    assert verified <= recorded


# --- model parsing through the real classes --------------------------------

async def _identify(client, data):
    await client._callbacks["identify"](client, data)
    return client


PARSERS = {
    "fetch_member_by_handle": lambda c, d: [c._replace_member(d["member"])],
    "fetch_member_by_id": lambda c, d: [c._replace_member(d["member"])],
    "fetch_lobby_info": lambda c, d: [c._replace_lobby(d)],
    "fetch_history": lambda c, d: [c._replace_message(m) for m in d["messages"]],
    "fetch_threads": lambda c, d: [c._replace_thread_stub(t) for t in d["threads"]],
    "fetch_thread_nested": lambda c, d: [c._replace_thread(d)],
    "fetch_thread_classic": lambda c, d: [c._replace_thread(d)],
}
EXPECTED_TYPES = {
    "fetch_member_by_handle": Member, "fetch_member_by_id": Member, "fetch_lobby_info": Lobby,
    "fetch_history": Message, "fetch_threads": ThreadStub, "fetch_thread_nested": Thread,
    "fetch_thread_classic": Thread,
}


@pytest.mark.parametrize("path", [p for p in HTTP_FIXTURES if p.parent.name in PARSERS or p.parent.name == "identify"],
                         ids=fid)
async def test_http_fixture_parses_through_models(path):
    fx = load(path)
    data = fx["response"]["data"]
    client = HTTPClient()
    try:
        if fx["operationId"] == "identify":
            await _identify(client, data)
            assert client._ready_event.is_set()
            assert len(client.communities) == len(data["communities"])
            for community in client.communities:
                assert community.lobbies and community.forums
            return
        objs = PARSERS[fx["operationId"]](client, data)
        assert objs and all(isinstance(o, EXPECTED_TYPES[fx["operationId"]]) for o in objs)
        if fx["operationId"] == "fetch_thread_nested":
            assert len(objs[0].replies) == len(data.get("replies", []))
    finally:
        await client.close()


# --- websocket ---------------------------------------------------------------

def event_validator(event_type):
    return speclib.schema_validator(f"events/{event_type}.json")


@pytest.mark.parametrize("path", WS_FIXTURES, ids=fid)
def test_ws_fixture_matches_event_schema(path):
    fx = load(path)
    assert fx["event"]["type"] == path.parent.name
    errors = list(event_validator(path.parent.name).iter_errors(fx["event"]))
    assert not errors, [f"{list(e.absolute_path)}: {e.message}" for e in errors]


@pytest.mark.parametrize("path", WS_FIXTURES, ids=fid)
async def test_ws_fixture_dispatches_to_callback(path):
    fx = load(path)
    calls = []

    class Recorder(Client):
        pass

    client = Recorder()
    try:
        async def record(*args, **kwargs):
            calls.append((args, kwargs))

        setattr(client, fx["expect"], record)
        setup = fx.get("setup", {})
        for m in setup.get("members", []):
            client._replace_member(m)
        for lobby in setup.get("lobbies", []):
            client._replace_lobby(lobby)

        task = await client._dispatch_event(fx["event"]["type"], fx["event"])
        assert task is not None
        await task
        for _ in range(3):
            await asyncio.sleep(0)
        assert calls, f"{fx['expect']} was not called"
    finally:
        await client.close()


async def test_unknown_event_goes_to_unhandled_event():
    seen = []
    client = Client()
    try:
        if "unhandled_event" not in client._callbacks:
            pytest.skip("no unhandled_event handler registered")
        orig = client._callbacks["unhandled_event"]
        client._callbacks = {**client._callbacks, "unhandled_event": lambda self, p: _record(seen, p)}
        task = await client._dispatch_event("totally.new.event", {"type": "totally.new.event"})
        await task
        assert seen == [{"type": "totally.new.event"}]
        client._callbacks["unhandled_event"] = orig
    finally:
        await client.close()


async def _record(seen, payload):
    seen.append(payload)
