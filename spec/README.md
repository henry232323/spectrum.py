# spec/

A machine-readable description of the RSI Spectrum protocol as spectrum.py uses it. It is the source of
truth that the Python package (and, later, a JS package) is checked against. Unofficial: these are the
undocumented endpoints the Spectrum web client uses, and they can change at any time.

| Path | What |
|---|---|
| `VERSION` | Spec version, calendar-based (`2026.11.0`). Bump on any change. |
| `openapi/spectrum.yaml` | OpenAPI 3.1 root for Spectrum HTTP. `paths/*.yaml` holds one file per area. |
| `asyncapi/spectrum-ws.yaml` | AsyncAPI 3.0 for the websocket: client frames and server events. |
| `schemas/*.json` | JSON Schema 2020-12 for the models, shared by both documents. `schemas/events/` has one per event. |
| `policy.yaml` | Header and cookie names, URLs, retry numbers, error-code map. |
| `fixtures/` | Redacted request/response pairs and websocket frames. See `fixtures/README.md`. |

## Conventions

* `operationId` is the `spectrum.http.HTTP` method name, so generated code can keep today's names.
* Every Spectrum operation is a `POST`; the `200` response is the envelope (`schemas/envelope.json`)
  with `data` narrowed where we know the shape.
* `x-spectrum` on each operation:
  * `python`: the method implementing it; `constant`: the endpoint constant in `spectrum.http`;
  * `auth`: `anonymous` (observed to work without a session), `session`, or `unknown`;
  * `verified`: `true` only when a recorded fixture backs the response shape;
  * `write`: the call changes state. Don't feature these in docs or examples.
* Schemas are lenient on purpose: `additionalProperties: true`, IDs are numeric strings (or integers),
  PHP-style empty collections may arrive as `[]`. Required keys are the ones the Python models index
  directly, so a schema failure means the current code would break.
* The experimental gRPC transport is deliberately not described.
* Other RSI sites (Orgs, Starmap, Roadmap, GraphQL services) are not covered yet; their `.graphql`
  documents stay inside the Python package for now.

## Provenance

The first draft of `openapi/` and `asyncapi/` (and `schemas/events/`) was emitted by
`scripts/bootstrap_spec.py` from `src/spectrum/http.py` and `src/spectrum/client.py`. Those files are
maintained by hand from here on. Model schemas, `policy.yaml` and fixtures were written by hand.

## Checks

`python -m pytest` validates the documents, checks every fixture against its schema, parses every
fixture through the real model classes, dispatches every websocket fixture through `Client`, and
checks that the spec and the code still list the same operations and events.
