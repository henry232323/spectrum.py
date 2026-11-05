# Fixtures

`http/<operationId>/<case>.json` and `ws/<event-type>/<case>.json`. Both test suites replay them.

## HTTP fixture format

```json
{
  "operationId": "fetch_member_by_handle",
  "source": "recorded",            // or "synthesized: ..."
  "recorded_at": "2026-11-04",
  "auth": "anonymous",
  "request": { ... },              // JSON body sent
  "status": 200,
  "response": { "success": 1, "code": "OK", "msg": "OK", "data": { ... } }
}
```

## WS fixture format

```json
{
  "source": "...",
  "expect": "on_message",          // Client callback that must fire
  "setup": { "members": [], "lobbies": [] },   // optional: objects to put in the client cache first
  "event": { "type": "message.new", ... }       // the frame as received
}
```

## Recording

```shell
python scripts/record.py fetch_member_by_handle '{"nickname": "SomeHandle"}' --case default
```

* Anonymous, public, read-only endpoints only. No cookies or tokens are sent.
* One request per run, at least 2 s apart.
* Never record DMs, private or group lobbies.

## Redaction (mandatory)

This repository is public. Everything goes through `scripts/redact.py` before it is written:

* tokens, JWTs, device and player IDs become `<redacted>`;
* each member gets a stable fake identity (`1000001` / `Citizen1`); references to their ID elsewhere
  (`member_id`, `erased_by`, reaction member sets, reply reference labels) are rewritten to match;
* message and post text, thread subjects and slugs, and signatures become placeholder text; entity
  and style ranges are cleared; links and media URLs in user content become `https://example.invalid/...`;
* organisation badges and per-community role memberships become generic values;
* long lists are cut to 3 items.

Content IDs (message, thread, reply, lobby, channel) are left as recorded: they point at public posts,
and the schemas need them to stay consistent. `tests/test_fixtures.py` runs `redact.find_leaks` over
every fixture.

WS fixtures are synthesized from the recorded HTTP payloads until a redacted live capture exists.
