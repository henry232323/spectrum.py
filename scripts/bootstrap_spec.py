"""One-off bootstrap: emit the first draft of spec/ from the current Python code.

    python scripts/bootstrap_spec.py [--force]

Reads ``src/spectrum/http.py`` (endpoint constants, ``HTTP`` method names and the
sample JSON in their docstrings) and ``src/spectrum/client.py`` (the
``@register_callback`` websocket handlers), and writes:

* ``spec/openapi/spectrum.yaml`` and ``spec/openapi/paths/*.yaml``
* ``spec/asyncapi/spectrum-ws.yaml``
* ``spec/schemas/events/*.json``

After the first run the spec files are the source of truth and are edited by
hand. Re-running refuses to overwrite them unless ``--force`` is given. The
hand-written model schemas (``spec/schemas/*.json``), ``policy.yaml`` and the
fixtures are never touched by this script.
"""
from __future__ import annotations

import argparse
import ast
import json
import pathlib
import re
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "spectrum"
SPEC = ROOT / "spec"
sys.path.insert(0, str(ROOT / "scripts"))

import redact  # noqa: E402

SPECTRUM_PREFIX = "/api/spectrum/"

# Path segment -> paths/<file>.yaml
AREA = {
    "friend": "social", "friend-request": "social", "blocklist": "social",
    "bookmark": "social", "bookmarks": "social",
    "vote": "reaction", "reaction": "reaction",
    "emoji": "community", "community": "community",
    "flag": "moderation", "moderation": "moderation",
    "broadcast-message": "notification", "notification": "notification",
    "subscription": "notification",
}
V2_AREA = {"guide": "v2-guide", "community": "v2-community", "lobby": "v2-lobby", "forum": "v2-forum",
           "member": "v2-member", "bookmark": "v2-social"}

# Operations whose data payload is described by a shared schema. `verified`
# means a recorded fixture backs the shape; others come from docstrings and code.
DATA_SCHEMAS = {
    "identify": ("identify.json", True),
    "fetch_member_by_handle": ("member-info.json", True),
    "fetch_member_by_id": ("member-info.json", False),
    "fetch_lobby_info": ("lobby.json", True),
    "fetch_history": ("message-history.json", True),
    "fetch_threads": ("thread-list.json", True),
    "fetch_thread_nested": ("thread.json", True),
    "fetch_thread_classic": ("thread.json", False),
    "send_message": ("message.json", False),
    "edit_message": ("message.json", False),
    "send_reply": ("reply.json", False),
    "create_thread": ("thread.json", False),
}
# Observed to work without a session (anonymous, read-only).
ANONYMOUS_OK = {"identify", "fetch_member_by_handle", "fetch_lobby_info", "fetch_history",
                "fetch_threads", "fetch_thread_nested"}
WRITE_HINTS = ("create", "edit", "erase", "remove", "add", "send", "set", "delete", "move", "kick",
               "ban", "accept", "decline", "cancel", "block", "unblock", "pin", "sink", "close",
               "lock", "upload", "transfer", "join", "leave", "invite", "mark", "read", "subscribe",
               "update", "report", "flag", "vote", "react", "start", "end", "clear", "toggle")

# Methods that do not go through make_request(CONSTANT, payload).
SPECIAL = {
    "identify": {"path": "/api/spectrum/auth/identify", "body": "json", "area": "auth",
                 "note": "Uses its own session. Returns the bootstrap state and a JWT for the websocket."},
    "create_thread": {"const": "CREATE_THREAD", "body": "json",
                      "note": "Retried up to 6 times while an image block is still processing ('Invalid image block data')."},
    "set_motd": {"path": "/api/spectrum/lobby/setMotd", "body": "json"},
    "fetch_embed": {"path": "/api/spectrum/media/embed/fetch", "body": "json",
                    "sample": {"url": "https://example.com/"}},
    "upload_image": {"path": "/api/spectrum/media/upload/image", "body": "multipart"},
    "upload_emoji": {"const": "UPLOAD_EMOJI", "body": "multipart"},
    "v2_community_emoji_upload": {"const": "V2_COMMUNITY_EMOJI_UPLOAD", "body": "multipart"},
}
SKIP = {"close", "make_request", "_create_thread_request"}


def area_for(path: str) -> str:
    rest = path[len(SPECTRUM_PREFIX):]
    parts = rest.split("/")
    if parts[0] == "v2":
        return V2_AREA.get(parts[1], "v2-misc")
    if parts[0] == "auth":
        return "auth"
    return AREA.get(parts[0], parts[0])


def json_samples(doc: str) -> list:
    out = []
    for line in (doc or "").splitlines():
        line = line.strip()
        if line[:1] in "{[":
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
    return out


def infer(value):
    """Loose type from one docstring sample. Scalars may also be null: samples rarely show every case."""
    if value is None:
        return {}
    if isinstance(value, bool):
        return {"type": ["boolean", "null"]}
    if isinstance(value, int):
        return {"type": ["integer", "null"]}
    if isinstance(value, float):
        return {"type": ["number", "null"]}
    if isinstance(value, str):
        if value.isdigit():
            return {"type": ["string", "integer", "null"], "pattern": r"^\d+$"}
        return {"type": ["string", "null"]}
    if isinstance(value, list):
        return {"type": "array"}
    return {"type": "object", "additionalProperties": True}


def request_schema(samples: list) -> dict:
    props: dict = {}
    for s in samples:
        if isinstance(s, dict):
            for k, v in s.items():
                props.setdefault(k, infer(v))
    schema = {"type": "object", "additionalProperties": True}
    if props:
        schema["properties"] = props
    return schema


def scan_http():
    tree = ast.parse((SRC / "http.py").read_text())
    consts = {n.targets[0].id: n.value.value for n in tree.body
              if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
              and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)}
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "HTTP")
    ops = []
    for fn in cls.body:
        if not isinstance(fn, ast.AsyncFunctionDef) or fn.name in SKIP:
            continue
        doc = ast.get_docstring(fn) or ""
        op = {"name": fn.name, "doc": doc, "samples": json_samples(doc), "params": [], "body": "json"}
        special = SPECIAL.get(fn.name)
        if special:
            op["path"] = special.get("path") or consts[special["const"]]
            op["body"] = special["body"]
            op["note"] = special.get("note")
            if "sample" in special:
                op["samples"] = [special["sample"]]
        else:
            calls = [c for c in ast.walk(fn) if isinstance(c, ast.Call) and getattr(c.func, "attr", "") == "make_request"]
            if len(calls) != 1:
                raise SystemExit(f"cannot classify {fn.name}")
            arg = calls[0].args[0]
            if isinstance(arg, ast.Name) and arg.id in consts:
                op["path"] = consts[arg.id]
                op["const"] = arg.id
            elif isinstance(arg, ast.Name) and arg.id == "endpoint":
                fstr = next(a.value for a in ast.walk(fn) if isinstance(a, ast.Assign)
                            and getattr(a.targets[0], "id", "") == "endpoint")
                path = "".join(p.value if isinstance(p, ast.Constant) else "{" + ast.unparse(p.value) + "}"
                               for p in fstr.values)
                op["path"] = path
                op["params"] = re.findall(r"{(\w+)}", path)
            else:
                raise SystemExit(f"cannot classify {fn.name}: {ast.unparse(arg)}")
        if fn.name.startswith("v2_"):
            op["since"] = "v2"
        ops.append(op)
    return ops


def operation(op: dict) -> dict:
    name = op["name"]
    summary = op["doc"].splitlines()[0].strip() if op["doc"] and not op["doc"].lstrip().startswith(("{", "[")) else None
    data_schema, verified = DATA_SCHEMAS.get(name, (None, False))
    is_write = any(h in name.split("_") for h in WRITE_HINTS) and not name.startswith(("fetch", "get", "list", "search"))
    x = {
        "python": f"HTTP.{name}",
        "auth": "anonymous" if name in ANONYMOUS_OK else ("session" if is_write else "unknown"),
        "verified": verified,
        "write": is_write,
    }
    if op.get("since"):
        x["since"] = "v2"
    if op.get("const"):
        x["constant"] = op["const"]
    out: dict = {"operationId": name, "tags": [area_for(op["path"])]}
    if summary:
        out["summary"] = summary
    if op.get("note"):
        out["description"] = op["note"]
    out["x-spectrum"] = x
    if op["params"]:
        out["parameters"] = [{"name": p, "in": "path", "required": True, "schema": {"type": "string"}}
                             for p in op["params"]]
    if op["body"] == "multipart":
        out["requestBody"] = {"required": True, "content": {"multipart/form-data": {"schema": {
            "type": "object", "required": ["file"], "properties": {"file": {"type": "string", "format": "binary"}},
            "additionalProperties": True}}}}
    else:
        samples = [redact.redact_fixture(s, max_items=None) for s in op["samples"]]
        media: dict = {"schema": request_schema(samples)}
        if samples:
            media["examples"] = {f"sample{i + 1}": {"value": s} for i, s in enumerate(samples)}
        out["requestBody"] = {"required": True, "content": {"application/json": media}}
    data = {"$ref": f"../../schemas/{data_schema}"} if data_schema else {}
    out["responses"] = {
        "200": {
            "description": "Envelope. `success` is 1 on success; `data` holds the result.",
            "content": {"application/json": {"schema": {
                "allOf": [{"$ref": "../../schemas/envelope.json"}, {"properties": {"data": data}}]}}},
        },
        "default": {
            "description": "Error envelope (`success` 0, `code` e.g. ErrAccessDenied), or a non-JSON error page.",
            "content": {"application/json": {"schema": {"$ref": "../../schemas/envelope.json"}}},
        },
    }
    return out


def build_openapi(ops):
    by_area: dict[str, dict] = {}
    root_paths: dict = {}
    seen: dict[str, str] = {}
    for op in ops:
        path = op["path"]
        if path in seen:
            raise SystemExit(f"{op['name']} and {seen[path]} share {path}")
        seen[path] = op["name"]
        area = area_for(path)
        by_area.setdefault(area, {})[path] = {"post": operation(op)}
        pointer = path.replace("~", "~0").replace("/", "~1")
        root_paths[path] = {"$ref": f"paths/{area}.yaml#/{pointer}"}
    root = {
        "openapi": "3.1.0",
        "info": {
            "title": "RSI Spectrum HTTP API (unofficial)",
            "version": (SPEC / "VERSION").read_text().strip() if (SPEC / "VERSION").exists() else "2026.11.0",
            "summary": "Community description of the undocumented endpoints the Spectrum web client uses.",
            "description": (
                "Not made, endorsed or supported by Cloud Imperium Games or Roberts Space Industries. "
                "Every operation is a POST with a JSON body (multipart for uploads) returning the "
                "envelope in schemas/envelope.json. `x-spectrum.verified: false` means the shape comes "
                "only from code and docstring samples, not from a recorded response."
            ),
            "license": {"name": "MIT", "identifier": "MIT"},
        },
        "servers": [{"url": "https://robertsspaceindustries.com"}],
        "security": [{}, {"rsiToken": [], "rsiTokenCookie": [], "rsiDevice": []}],
        "tags": [{"name": a} for a in sorted(by_area)],
        "paths": dict(sorted(root_paths.items())),
        "components": {"securitySchemes": {
            "rsiToken": {"type": "apiKey", "in": "header", "name": "X-Rsi-Token",
                         "description": "Same value as the Rsi-Token cookie; acts as the CSRF token."},
            "rsiTokenCookie": {"type": "apiKey", "in": "cookie", "name": "Rsi-Token"},
            "rsiDevice": {"type": "apiKey", "in": "cookie", "name": "_rsi_device"},
        }},
    }
    return root, by_area


def scan_events():
    tree = ast.parse((SRC / "client.py").read_text())
    events = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.AsyncFunctionDef):
            continue
        for dec in node.decorator_list:
            if isinstance(dec, ast.Call) and getattr(dec.func, "id", "") == "register_callback":
                name = dec.args[0].value
                if name == "unhandled_event":  # catch-all, not a wire event
                    continue
                required, optional = [], []
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Subscript) and isinstance(sub.value, ast.Name) and sub.value.id == "payload" \
                            and isinstance(sub.slice, ast.Constant):
                        required.append(sub.slice.value)
                    if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr == "get" \
                            and isinstance(sub.func.value, ast.Name) and sub.func.value.id == "payload" and sub.args \
                            and isinstance(sub.args[0], ast.Constant):
                        optional.append(sub.args[0].value)
                callbacks = sorted({c.func.attr for c in ast.walk(node) if isinstance(c, ast.Call)
                                    and isinstance(c.func, ast.Attribute) and c.func.attr.startswith("on_")
                                    and isinstance(c.func.value, ast.Name) and c.func.value.id == "self"})
                events[name] = {"required": list(dict.fromkeys(required)),
                                "optional": [o for o in dict.fromkeys(optional) if o not in required],
                                "handler": node.name, "callbacks": callbacks}
    return events


EVENT_PROP_REFS = {"message": "message.json", "member": "member.json", "reaction": "reaction.json",
                   "message_lobby": "lobby.json", "forum_channel": "forum-channel.json",
                   "presence": "presence.json"}


def event_schema(name: str, info: dict) -> dict:
    props = {"type": {"const": name}}
    for key in info["required"] + info["optional"]:
        if key == "type":
            continue
        if key in EVENT_PROP_REFS:
            props[key] = {"$ref": f"../{EVENT_PROP_REFS[key]}"}
        elif key.endswith("_id"):
            props[key] = {"$ref": "../id.json"}
        else:
            props[key] = {}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": name,
        "description": f"Server -> client `{name}`. Required keys are the ones `Client.{info['handler']}` indexes directly.",
        "type": "object",
        "required": ["type", *[k for k in info["required"] if k != "type"]],
        "properties": props,
        "additionalProperties": True,
    }


def build_asyncapi(events: dict):
    messages, ops = {}, {}
    for name in sorted(events):
        mid = re.sub(r"[^A-Za-z0-9]+", "_", name)
        messages[mid] = {"name": name, "title": name,
                         "x-spectrum": {"python_callbacks": events[name]["callbacks"]},
                         "payload": {"$ref": f"../schemas/events/{name}.json"}}
    for mid, payload in [("subscribe", {
        "type": "object", "required": ["type", "subscription_keys"],
        "properties": {"type": {"const": "subscribe"},
                       "subscription_keys": {"type": "array", "items": {"type": "string"}},
                       "subscription_scope": {"type": ["string", "null"], "enum": [None, "content"]}}}),
            ("typing_start", {"type": "object", "required": ["type", "lobby_id"],
                              "properties": {"type": {"const": "message_lobby.typing.start"},
                                             "lobby_id": {"$ref": "../schemas/id.json"}}}),
            ("typing_end", {"type": "object", "required": ["type", "lobby_id"],
                            "properties": {"type": {"const": "message_lobby.typing.end"},
                                           "lobby_id": {"$ref": "../schemas/id.json"}}})]:
        messages["client_" + mid] = {"name": payload["properties"]["type"]["const"], "payload": payload}
    ops["receiveEvents"] = {"action": "receive", "channel": {"$ref": "#/channels/spectrum"},
                            "messages": [{"$ref": f"#/channels/spectrum/messages/{m}"}
                                         for m in messages if not m.startswith("client_")]}
    ops["sendFrames"] = {"action": "send", "channel": {"$ref": "#/channels/spectrum"},
                         "messages": [{"$ref": f"#/channels/spectrum/messages/{m}"}
                                      for m in messages if m.startswith("client_")]}
    return {
        "asyncapi": "3.0.0",
        "info": {
            "title": "RSI Spectrum websocket (unofficial)",
            "version": (SPEC / "VERSION").read_text().strip() if (SPEC / "VERSION").exists() else "2026.11.0",
            "description": (
                "JSON text frames shaped `{\"type\": \"<event>\", ...payload}`. Connect with the JWT from "
                "`auth/identify` as `?token=`. Unsubscribing is an HTTP call (`subscription/remove`), not a "
                "frame. There are no heartbeats; spectrum.py reconnects after 360 s without a frame "
                "(backoff 1 -> 60 s) and re-identifies for a fresh token. The experimental gRPC transport is "
                "deliberately not described here."
            ),
            "license": {"name": "MIT"},
        },
        "servers": {"production": {"host": "robertsspaceindustries.com", "pathname": "/ws/spectrum",
                                   "protocol": "wss", "security": [{"$ref": "#/components/securitySchemes/jwt"}]}},
        "channels": {"spectrum": {"address": "/ws/spectrum", "messages": messages}},
        "operations": ops,
        "components": {"securitySchemes": {"jwt": {
            "type": "httpApiKey", "in": "query", "name": "token",
            "description": "JWT from auth/identify `data.token`; also send header x-rsi-token."}}},
    }


def dump_yaml(path: pathlib.Path, data, header: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=110)
    path.write_text(header + text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    if (SPEC / "openapi" / "spectrum.yaml").exists() and not args.force:
        sys.exit("spec/openapi already exists; it is hand-maintained now. Use --force to overwrite.")
    header = "# Bootstrapped by scripts/bootstrap_spec.py, then maintained by hand.\n"
    ops = scan_http()
    root, by_area = build_openapi(ops)
    dump_yaml(SPEC / "openapi" / "spectrum.yaml", root, header)
    for area, paths in by_area.items():
        dump_yaml(SPEC / "openapi" / "paths" / f"{area}.yaml", dict(sorted(paths.items())), header)
    events = scan_events()
    for name, info in events.items():
        p = SPEC / "schemas" / "events" / f"{name}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(event_schema(name, info), indent=2) + "\n")
    dump_yaml(SPEC / "asyncapi" / "spectrum-ws.yaml", build_asyncapi(events), header)
    print(f"{len(ops)} operations in {len(by_area)} files, {len(events)} events")


if __name__ == "__main__":
    main()
