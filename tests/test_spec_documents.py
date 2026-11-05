"""The spec documents themselves are valid and internally consistent."""
import json

import pytest
from jsonschema import Draft202012Validator
from openapi_spec_validator import validate
from openapi_spec_validator.readers import read_from_filename

import speclib


def test_openapi_root_is_valid_openapi_31():
    root = speclib.SPEC / "openapi" / "spectrum.yaml"
    spec, base_uri = read_from_filename(str(root))
    assert spec["openapi"].startswith("3.1")
    validate(spec, base_uri=base_uri)


@pytest.mark.parametrize("path", sorted((speclib.SPEC / "openapi" / "paths").glob("[!._]*.yaml")), ids=lambda p: p.name)
def test_path_files_reference_existing_schemas(path):
    doc = speclib.load_file(path)
    refs = []

    def walk(o):
        if isinstance(o, dict):
            if "$ref" in o:
                refs.append(o["$ref"])
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(doc)
    for ref in refs:
        assert (path.parent / ref.split("#")[0]).resolve().exists(), ref


def all_schema_files():
    return sorted(p for p in speclib.SCHEMAS.rglob("*.json") if not p.name.startswith("._"))


@pytest.mark.parametrize("path", all_schema_files(), ids=lambda p: str(p.relative_to(speclib.SCHEMAS)))
def test_json_schemas_are_valid_and_refs_resolve(path):
    schema = json.loads(path.read_text())
    Draft202012Validator.check_schema(schema)
    # Resolving every $ref proves no dangling references.
    validator = speclib.validator_for(schema, path)
    resolver = validator._resolver

    def walk(o):
        if isinstance(o, dict):
            if "$ref" in o:
                resolver.lookup(o["$ref"])
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(schema)


def test_asyncapi_structure():
    doc = speclib.load_asyncapi()
    assert doc["asyncapi"] == "3.0.0"
    channel = doc["channels"]["spectrum"]
    messages = channel["messages"]
    assert messages
    for mid, msg in messages.items():
        payload = msg["payload"]
        if "$ref" in payload:
            target = (speclib.SPEC / "asyncapi" / payload["$ref"]).resolve()
            assert target.exists(), payload["$ref"]
            assert json.loads(target.read_text())["properties"]["type"]["const"] == msg["name"]
        else:
            Draft202012Validator.check_schema(payload)
    for op in doc["operations"].values():
        assert op["action"] in ("send", "receive")
        for m in op["messages"]:
            assert m["$ref"].split("/")[-1] in messages


def test_versions_agree():
    version = (speclib.SPEC / "VERSION").read_text().strip()
    assert speclib.load_spectrum_spec().root["info"]["version"] == version
    assert speclib.load_asyncapi()["info"]["version"] == version


def test_grpc_is_not_in_the_spec():
    for path in speclib.SPEC.rglob("*"):
        if path.is_file() and not path.name.startswith("._") and path.suffix in (".yaml", ".json"):
            assert "/grpc/" not in path.read_text(), path
