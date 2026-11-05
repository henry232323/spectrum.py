"""spec/ and the current Python code describe the same operations and events."""
import ast
import inspect

import pytest

import speclib
import spectrum.http as http_mod
from spectrum import Client
from spectrum.http import HTTP

SPEC = speclib.load_spectrum_spec()
INTERNAL = {"close", "make_request", "_create_thread_request"}


def http_methods():
    return {name for name, fn in inspect.getmembers(HTTP, inspect.iscoroutinefunction)
            if name not in INTERNAL and not name.startswith("__")}


def test_every_http_method_has_an_operation():
    assert http_methods() - set(SPEC.operations) == set()


def test_every_operation_has_an_http_method():
    assert set(SPEC.operations) - http_methods() == set()


def test_operation_x_spectrum_points_at_code():
    for op in SPEC.operations.values():
        assert op.x["python"] == f"HTTP.{op.operation_id}"
        assert op.x["auth"] in ("anonymous", "session", "unknown")
        assert isinstance(op.x["verified"], bool)
        if "constant" in op.x:
            assert getattr(http_mod, op.x["constant"]) == op.path, op.operation_id


def test_every_spectrum_endpoint_constant_is_in_the_spec():
    tree = ast.parse(inspect.getsource(http_mod))
    paths = {n.value.value for n in tree.body if isinstance(n, ast.Assign)
             and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)
             and n.value.value.startswith("/api/spectrum/")}
    # FETCH_BROADCAST_MESSAGE_LIST is defined but no method uses it yet.
    unused = {http_mod.FETCH_BROADCAST_MESSAGE_LIST}
    spec_paths = {op.path for op in SPEC.operations.values()}
    assert paths - spec_paths - unused == set()


def test_every_registered_event_is_in_asyncapi():
    doc = speclib.load_asyncapi()
    names = {m["name"] for m in doc["channels"]["spectrum"]["messages"].values()}
    registered = set(Client._callbacks) - {"identify", "unhandled_event"}
    assert registered - names == set()


@pytest.mark.parametrize("op_id", sorted(SPEC.operations))
def test_operations_are_post_with_envelope(op_id):
    op = SPEC.operation(op_id)
    assert op.method == "post"
    schema = op.raw["responses"]["200"]["content"]["application/json"]["schema"]
    assert schema["allOf"][0]["$ref"].endswith("envelope.json")
