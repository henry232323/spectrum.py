"""Phase-0 (0.1.1) fixes: packaging, logging, User-Agent, experimental gRPC."""
import pathlib
import subprocess
import sys

import warnings

import pytest

import speclib
import spectrum
from spectrum.http import DEFAULT_USER_AGENT

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "src"


def run_py(code: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                          env={"PYTHONPATH": str(SRC), "PATH": ""}, cwd="/")


def test_import_does_not_configure_root_logging():
    r = run_py("import logging, spectrum; print(len(logging.getLogger().handlers))")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "0"


def test_sub_clients_survive_missing_aiographql():
    code = """
import sys, importlib.abc
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path, target=None):
        if name == 'aiographql' or name.startswith('aiographql.'):
            raise ImportError('blocked for test')
sys.meta_path.insert(0, Block())
import spectrum
missing = [n for n in ('OrgsClient','StarmapClient','RoadmapClient','RSIClient','GalactapediaClient',
                       'CIGClient','IssueCouncilClient','HTTPClient','Client') if not hasattr(spectrum, n)]
print('missing', missing)
print('community', hasattr(spectrum, 'CommunityHubClient'))
"""
    r = run_py(code)
    assert r.returncode == 0, r.stderr
    assert "missing []" in r.stdout
    assert "community False" in r.stdout


def test_pyproject_extras_and_package_data():
    tomllib = pytest.importorskip("tomllib")
    data = tomllib.loads((ROOT / "pyproject.toml").read_text())
    project = data["project"]
    assert "aiographql-client" in project["optional-dependencies"]["community-hub"]
    assert "options" not in data
    globs = data["tool"]["setuptools"]["package-data"]["*"]
    assert any(g.endswith(".graphql") for g in globs) and any(g.endswith(".json") for g in globs)
    assert project["license"] == "MIT"
    assert all(u.startswith("https://") for u in project["urls"].values())
    for word in ("bot", "chatbot", "proof-of-concept", "selfbot", "scraper"):
        assert word not in project["description"].lower()
        assert word not in project["keywords"]


def test_graphql_documents_exist_in_package_tree():
    # They must be inside src/spectrum so package-data ships them.
    assert len([p for p in (SRC / "spectrum").rglob("*.graphql") if not p.name.startswith("._")]) > 100


def test_version():
    assert spectrum.__version__ == "0.1.1"


async def test_default_user_agent_is_honest():
    assert DEFAULT_USER_AGENT == f"spectrum.py/{spectrum.__version__} (+https://github.com/henry232323/spectrum.py)"
    client = spectrum.HTTPClient()
    try:
        assert client._http.headers["User-Agent"] == DEFAULT_USER_AGENT
        assert "Mozilla" not in client._http.headers["User-Agent"]
    finally:
        await client.close()


async def test_user_agent_is_configurable():
    client = spectrum.Client(user_agent="my-tool/1.0")
    try:
        assert client._http.headers["User-Agent"] == "my-tool/1.0"
    finally:
        await client.close()


async def test_grpc_transport_warns_experimental():
    from spectrum.grpc_gateway import ExperimentalTransportWarning
    with pytest.warns(ExperimentalTransportWarning, match="experimental"):
        client = spectrum.Client(transport="grpc")
    await client.close()


async def test_ws_transport_does_not_warn():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        client = spectrum.Client()
    await client.close()


def test_send_reply_uses_reply_endpoint():
    import inspect
    from spectrum.http import HTTP
    assert "CREATE_REPLY" in inspect.getsource(HTTP.send_reply)


def test_policy_matches_code():
    import spectrum.gateway as gateway
    from spectrum.errors import exception_map
    from spectrum.http import HTTP
    policy = speclib.load_file(speclib.SPEC / "policy.yaml")
    assert policy["http"]["user_agent"].format(version=spectrum.__version__) == DEFAULT_USER_AGENT
    assert str(gateway.Gateway.DEFAULT_GATEWAY) == policy["websocket"]["url"]
    assert gateway.Gateway._max_heartbeat_timeout == policy["websocket"]["receive_timeout_seconds"]
    assert gateway.Gateway._max_backoff == policy["websocket"]["backoff_seconds"]["max"]
    assert HTTP.MAX_RETRIES == policy["retry"]["max_attempts"]
    assert HTTP.RETRY_BACKOFF == policy["retry"]["backoff_seconds"]
    assert {k: v.__name__ for k, v in exception_map.items()} == policy["errors"]
