"""Record one Spectrum HTTP fixture, redacted.

    python scripts/record.py <operationId> '<json request body>' [--case NAME] [--raw-out PATH]

* Anonymous only: no cookies or tokens are ever sent. (Session recording is
  deliberately not supported here; hand-write those fixtures from a test account.)
* One request per invocation; consecutive invocations wait so calls are >= 2 s apart.
* The response goes through ``scripts/redact.py`` before anything is written to
  ``spec/fixtures/http/<operationId>/<case>.json``. ``--raw-out`` keeps the
  unredacted response for debugging; point it OUTSIDE the repository.

The operation's path is read from ``spec/openapi`` so the spec stays the source
of truth.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import redact  # noqa: E402
import speclib  # noqa: E402
from spectrum.http import DEFAULT_USER_AGENT  # noqa: E402

BASE = "https://robertsspaceindustries.com"
STAMP = pathlib.Path("/tmp/spectrum-record.last")
MIN_SPACING = 2.0


def _pace():
    try:
        last = float(STAMP.read_text())
    except (OSError, ValueError):
        last = 0.0
    wait = MIN_SPACING - (time.time() - last)
    if wait > 0:
        time.sleep(wait)
    STAMP.write_text(str(time.time()))


def fetch(path: str, body: dict) -> tuple[int, dict]:
    _pace()
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode(),
        method="POST",
        headers={
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Origin": BASE,
            "X-Tavern-action-id": "1",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("operation_id")
    ap.add_argument("body", nargs="?", default="{}")
    ap.add_argument("--case", default="default")
    ap.add_argument("--raw-out")
    ap.add_argument("--max-items", type=int, default=3, help="truncate long lists")
    args = ap.parse_args()

    op = speclib.load_spectrum_spec().operation(args.operation_id)
    if op.path_params:
        sys.exit("operations with path parameters must be recorded by hand")
    body = json.loads(args.body)
    status, response = fetch(op.path, body)
    if args.raw_out:
        raw = pathlib.Path(args.raw_out).resolve()
        if ROOT in raw.parents:
            sys.exit("--raw-out must be outside the repository")
        raw.write_text(json.dumps({"request": body, "status": status, "response": response}, indent=2))

    fixture = redact.redact_fixture(
        {"operationId": args.operation_id, "request": body, "status": status, "response": response},
        max_items=args.max_items,
    )
    out = ROOT / "spec" / "fixtures" / "http" / args.operation_id / f"{args.case}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(fixture, indent=2, ensure_ascii=False) + "\n")
    print(f"{status} -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
