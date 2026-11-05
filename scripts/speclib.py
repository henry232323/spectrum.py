"""Load spec/ and build JSON Schema validators for it. Used by the tests and scripts.

Dev-only: needs ``pyyaml`` and ``jsonschema`` (``pip install -e .[dev]``).
"""
from __future__ import annotations

import dataclasses
import functools
import json
import pathlib

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

ROOT = pathlib.Path(__file__).resolve().parent.parent
SPEC = ROOT / "spec"
SCHEMAS = SPEC / "schemas"
FIXTURES = SPEC / "fixtures"


def load_file(path: pathlib.Path):
    text = path.read_text()
    return yaml.safe_load(text) if path.suffix in (".yaml", ".yml") else json.loads(text)


def _retrieve(uri: str) -> Resource:
    if not uri.startswith("file://"):
        raise LookupError(f"refusing to fetch remote schema {uri}")
    path = pathlib.Path(uri[len("file://"):].split("#", 1)[0])
    return Resource.from_contents(load_file(path), default_specification=DRAFT202012)


@functools.lru_cache(maxsize=None)
def registry() -> Registry:
    return Registry(retrieve=_retrieve)


def validator_for(schema: dict, base: pathlib.Path) -> Draft202012Validator:
    """Validator for ``schema`` whose relative $refs resolve against file ``base``."""
    rooted = {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": base.resolve().as_uri(), **schema}
    return Draft202012Validator(rooted, registry=registry())


def schema_validator(name: str) -> Draft202012Validator:
    path = SCHEMAS / name
    return validator_for(load_file(path), path)


@dataclasses.dataclass
class Operation:
    operation_id: str
    path: str
    method: str
    file: pathlib.Path
    raw: dict

    @property
    def path_params(self) -> list[str]:
        return [p["name"] for p in self.raw.get("parameters", []) if p.get("in") == "path"]

    @property
    def x(self) -> dict:
        return self.raw.get("x-spectrum", {})

    def response_validator(self, status: str = "200") -> Draft202012Validator:
        schema = self.raw["responses"][status]["content"]["application/json"]["schema"]
        return validator_for(schema, self.file)

    def request_schema(self) -> dict | None:
        content = self.raw.get("requestBody", {}).get("content", {})
        media = content.get("application/json")
        return media["schema"] if media else None


class SpectrumSpec:
    def __init__(self, root_file: pathlib.Path):
        self.root_file = root_file
        self.root = load_file(root_file)
        self.operations: dict[str, Operation] = {}
        for path, item in self.root["paths"].items():
            if "$ref" in item:
                file_part, _, pointer = item["$ref"].partition("#")
                file = (root_file.parent / file_part).resolve()
                doc = load_file(file)
                key = pointer.lstrip("/").replace("~1", "/").replace("~0", "~")
                item = doc[key]
            else:
                file = root_file
            for method, op in item.items():
                if method in ("get", "post", "put", "patch", "delete"):
                    self.operations[op["operationId"]] = Operation(op["operationId"], path, method, file, op)

    def operation(self, operation_id: str) -> Operation:
        return self.operations[operation_id]


@functools.lru_cache(maxsize=None)
def load_spectrum_spec() -> SpectrumSpec:
    return SpectrumSpec(SPEC / "openapi" / "spectrum.yaml")


@functools.lru_cache(maxsize=None)
def load_asyncapi() -> dict:
    return load_file(SPEC / "asyncapi" / "spectrum-ws.yaml")


def http_fixtures():
    for path in sorted((FIXTURES / "http").glob("*/*.json")):
        if not path.name.startswith("._"):
            yield path


def ws_fixtures():
    for path in sorted((FIXTURES / "ws").glob("*/*.json")):
        if not path.name.startswith("._"):
            yield path
