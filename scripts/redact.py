"""Redaction for spec fixtures. Mandatory before anything is written to spec/fixtures/.

The repository is public. Fixtures must never contain secrets, and must not
become a dump of real players' data. ``redact_fixture`` rewrites a recorded
``{request, response}`` pair so that:

* tokens, JWTs, device IDs and player IDs are replaced with ``<redacted>``;
* every member object (anything with ``nickname``/``displayname``) gets a stable
  fake identity (``1000001`` / ``Citizen1``), and every reference to that
  member's ID elsewhere in the document is rewritten to the same fake ID;
* user-written text (message and post text, thread subjects and slugs,
  signatures) becomes neutral placeholder text, and entity/style ranges that
  pointed into the original text are cleared;
* links and media URLs inside user content become ``https://example.invalid/...``;
* organisation badges and per-community role memberships (which reveal
  affiliations) are replaced with generic values;
* long lists are truncated to ``max_items``.

``find_leaks`` is used by the test suite to check committed fixtures.
"""
from __future__ import annotations

import copy
import re
from typing import Any

JWT_RE = re.compile(r"eyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]*")
SECRET_KEYS = {
    "token", "gameToken", "playerId", "rsi_token", "Rsi-Token", "X-Rsi-Token",
    "device_id", "_rsi_device", "jwt", "access_token", "refresh_token",
}
TEXT_KEYS = {"text", "plaintext", "annotation_plaintext"}
MEMBER_REF_KEYS = {"member_id", "erased_by", "leader_id", "author_id", "creator_id", "owner_id"}
MEMBER_REF_LIST_KEYS = {"member_ids"}
USER_CONTENT_KEYS = {"content_blocks", "content_state", "media", "media_preview", "lexical_content", "embed"}
PLACEHOLDER_URL = "https://example.invalid/redacted"
DEFAULT_AVATAR = "https://cdn.robertsspaceindustries.com/static/images/account/avatar_default_big.jpg"
GENERIC_ORG_ICON = "https://cdn.robertsspaceindustries.com/static/images/organization/defaults/thumbnail/generic.png"
FAKE_ID_BASE = 1000000
# Only the main Star Citizen community's role list is kept on member objects.
KEEP_ROLE_COMMUNITIES = {"1"}


def is_member(obj: Any) -> bool:
    return isinstance(obj, dict) and "id" in obj and ("nickname" in obj or "displayname" in obj)


class Redactor:
    def __init__(self, max_items: int | None = 3):
        self.max_items = max_items
        self.ids: dict[str, str] = {}
        self.names: dict[str, str] = {}
        self.slugs: dict[str, str] = {}
        self.text_n = 0

    # --- identity maps -----------------------------------------------------
    def fake_id(self, real: Any) -> str:
        key = str(real)
        if key not in self.ids:
            self.ids[key] = str(FAKE_ID_BASE + len(self.ids) + 1)
        return self.ids[key]

    def fake_name(self, real: str) -> str:
        if real not in self.names:
            self.names[real] = f"Citizen{len(self.names) + 1}"
        return self.names[real]

    def fake_slug(self, real: str) -> str:
        if real not in self.slugs:
            self.slugs[real] = f"redacted-thread-{len(self.slugs) + 1}"
        return self.slugs[real]

    def fake_text(self) -> str:
        self.text_n += 1
        return f"Redacted text {self.text_n}."

    # --- passes --------------------------------------------------------------
    def collect_members(self, obj: Any):
        if is_member(obj):
            fid = self.fake_id(obj["id"])
            n = int(fid) - FAKE_ID_BASE
            for key in ("nickname", "displayname"):
                if isinstance(obj.get(key), str):
                    self.names.setdefault(obj[key], f"Citizen{n}")
        if isinstance(obj, dict):
            for v in obj.values():
                self.collect_members(v)
        elif isinstance(obj, list):
            for v in obj:
                self.collect_members(v)

    def redact_member(self, m: dict) -> dict:
        out = dict(m)
        out["id"] = self.fake_id(m["id"])
        for key in ("nickname", "displayname"):
            if isinstance(m.get(key), str):
                out[key] = self.fake_name(m[key])
        if "avatar" in out:
            out["avatar"] = DEFAULT_AVATAR
        if "signature" in out:
            out["signature"] = ""
        meta = out.get("meta")
        if isinstance(meta, dict) and isinstance(meta.get("badges"), list):
            badges = []
            for b in meta["badges"]:
                if isinstance(b, dict) and b.get("url"):
                    badges.append({"name": "Example Org", "icon": GENERIC_ORG_ICON,
                                   "url": "https://robertsspaceindustries.com/orgs/EXAMPLE"})
                else:
                    badges.append(b)
            out["meta"] = {**meta, "badges": badges}
        if isinstance(out.get("roles"), dict):
            out["roles"] = {k: v for k, v in out["roles"].items() if k in KEEP_ROLE_COMMUNITIES}
        return out

    def walk(self, obj: Any, key: str | None = None, in_content: bool = False, parent: dict | None = None) -> Any:
        if isinstance(obj, dict):
            if is_member(obj):
                obj = self.redact_member(obj)
            out = {}
            for k, v in obj.items():
                out[k] = self.walk_value(k, v, in_content or k in USER_CONTENT_KEYS, obj)
            return out
        if isinstance(obj, list):
            items = obj
            if self.max_items is not None and len(items) > self.max_items and items and isinstance(items[0], (dict, list)):
                items = items[: self.max_items]
            return [self.walk(v, key, in_content, parent) for v in items]
        if isinstance(obj, str):
            if JWT_RE.search(obj):
                return JWT_RE.sub("<redacted-jwt>", obj)
            if in_content and obj.startswith(("http://", "https://")):
                return PLACEHOLDER_URL
        return obj

    def walk_value(self, k: str, v: Any, in_content: bool, parent: dict) -> Any:
        if k in SECRET_KEYS and v not in (None, "", 0):
            return "<redacted>" if isinstance(v, str) else 0
        if k in TEXT_KEYS and isinstance(v, str) and v:
            return self.fake_text()
        if k == "subject" and isinstance(v, str) and v:
            return self.fake_text().rstrip(".")
        if k == "slug" and isinstance(v, str) and v and ("subject" in parent or "sort" in parent):
            return self.fake_slug(v)
        if k in ("entityRanges", "inlineStyleRanges") and isinstance(v, list):
            return []
        if k == "entityMap" and isinstance(v, (list, dict)):
            return [] if isinstance(v, list) else {}
        if k in MEMBER_REF_KEYS and isinstance(v, (str, int)) and str(v).isdigit():
            fake = self.fake_id(v)
            return fake if isinstance(v, str) else int(fake)
        if k in MEMBER_REF_LIST_KEYS and isinstance(v, list):
            return [self.fake_id(x) for x in v]
        if k == "members" and isinstance(v, dict) and all(str(x).isdigit() for x in v):
            # reaction member sets: {"<member_id>": ""}
            return {self.fake_id(mid): val for mid, val in list(v.items())[: self.max_items or None]}
        if k in ("nickname", "displayname", "handle", "label") and isinstance(v, str) and v in self.names:
            return self.names[v]
        return self.walk(v, k, in_content, parent)


def redact_fixture(fixture: dict, max_items: int | None = 3) -> dict:
    r = Redactor(max_items=max_items)
    fixture = copy.deepcopy(fixture)
    r.collect_members(fixture)
    return r.walk(fixture)


def find_leaks(obj: Any, path: str = "$") -> list[str]:
    """Return JSON paths of values that look like secrets or unredacted text."""
    problems = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}"
            if k in SECRET_KEYS and v not in (None, "", 0, "<redacted>"):
                problems.append(p)
            if is_member(obj) and k in ("nickname", "displayname") and isinstance(v, str) \
                    and not re.fullmatch(r"Citizen\d+", v):
                problems.append(p)
            if is_member(obj) and k == "id" and str(v).isdigit() and not int(v) > FAKE_ID_BASE:
                problems.append(p)
            if k in TEXT_KEYS and isinstance(v, str) and v and not v.startswith("Redacted text"):
                problems.append(p)
            problems += find_leaks(v, p)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            problems += find_leaks(v, f"{path}[{i}]")
    elif isinstance(obj, str) and JWT_RE.search(obj):
        problems.append(path)
    return problems
