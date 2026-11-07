import socket

import pytest

from .apihelp import TOKEN, Api
from .fakes import Scripted, plan


@pytest.fixture
def api(repo):
    a = Api(repo, Scripted([plan()]))
    yield a
    a.close()


def test_binds_loopback_only(api):
    assert api.server.server_address[0] == "127.0.0.1"


def test_api_needs_the_exact_token(api):
    assert api.json("GET", "/api/health", token=None)[0] == 401
    assert api.json("GET", "/api/health", token="wrong")[0] == 401
    assert api.json("GET", "/api/health", token=TOKEN[:-1])[0] == 401
    assert api.json("GET", "/api/health")[0] == 200
    assert api.json("GET", "/api/tasks", token=None)[0] == 401


def test_token_in_query_string_is_not_accepted(api):
    assert api.json("GET", f"/api/health?token={TOKEN}", token=None)[0] == 401


def test_bad_host_header_is_refused_even_with_token(api):   # DNS-rebinding defence
    assert api.json("GET", "/api/health", headers={"Host": "evil.example.com"})[0] == 403
    assert api.json("GET", "/api/health", headers={"Host": f"127.0.0.1:{api.port + 1}"})[0] == 403
    assert api.json("GET", "/api/health", headers={"Host": f"localhost:{api.port}"})[0] == 200


def test_cross_site_requests_are_refused(api):
    assert api.json("GET", "/api/health", headers={"Origin": "http://evil.example.com"})[0] == 403
    assert api.json("GET", "/api/health", headers={"Sec-Fetch-Site": "cross-site"})[0] == 403
    assert api.json("GET", "/api/health", headers={"Origin": f"http://127.0.0.1:{api.port}"})[0] == 200


def test_no_cors_headers_and_security_headers(api):
    status, _, head = api.call("GET", "/api/health")
    assert status == 200
    assert not any(k.lower().startswith("access-control") for k in head)
    assert head["X-Content-Type-Options"] == "nosniff" and head["Cache-Control"] == "no-store"
    assert "Server" not in head or "Python" not in head["Server"]


def test_body_must_be_json_and_small(api):
    assert api.json("POST", "/api/tasks", raw=b"goal=x", ctype="text/plain")[0] == 415
    assert api.json("POST", "/api/tasks", raw=b"{not json")[0] == 400
    assert api.json("POST", "/api/tasks", raw=b"[1]")[0] == 400
    try:   # the server refuses before reading the body, so the client may see 413 or a reset connection; either way nothing is accepted
        assert api.json("PUT", "/api/settings", raw=b'{"values":{"model":"' + b"a" * 1_100_000 + b'"}}')[0] == 413
    except OSError:
        pass
    # only task creation (attachments) may be big, and even that has a limit: the size is judged from Content-Length before anything is read
    assert api.json("POST", "/api/tasks", raw=b'{"goal":"x"}', headers={"Content-Length": "23000000"})[0] == 413
    assert api.json("GET", "/api/tasks")[1]["tasks"] == []


def test_unknown_endpoint_and_method(api):
    assert api.json("GET", "/api/nope")[0] == 404
    assert api.json("DELETE", "/api/health")[0] == 405


def test_task_ids_are_validated_so_paths_cannot_escape(api):
    for bad in ("..", "..%2F..%2Fetc", "20200101-000000-x/../../x", "%2e%2e"):
        assert api.json("GET", f"/api/tasks/{bad}")[0] in (400, 404)


def test_static_is_whitelisted_and_cannot_traverse(repo, tmp_path):
    web = tmp_path / "web"
    web.mkdir()
    (web / "index.html").write_text("<!doctype html><title>x</title>", encoding="utf-8")
    (web / ".secret").write_text("no", encoding="utf-8")
    (tmp_path / "outside.txt").write_text("outside", encoding="utf-8")
    a = Api(repo, Scripted([plan()]), web_dir=web)
    try:
        status, body, head = a.call("GET", "/", token=None)
        assert status == 200 and b"<title>x</title>" in body
        assert "script-src 'self'" in head["Content-Security-Policy"] and "frame-ancestors 'none'" in head["Content-Security-Policy"] and head["X-Frame-Options"] == "DENY"
        for path in ("/.secret", "/../outside.txt", "/%2e%2e/outside.txt", "/..%5coutside.txt", "/index.html/../../outside.txt", "/nothing.js"):
            status, body, _ = a.call("GET", path, token=None)
            assert status in (400, 403, 404) and b"outside" not in body and b"no" != body
    finally:
        a.close()


def test_keys_are_never_returned(api):
    assert api.json("PUT", "/api/keys/openai", {"value": "sk-SECRETSECRETSECRET1234"})[0] == 200
    status, body = api.json("GET", "/api/keys")
    assert status == 200 and body["keys"]["openai"] is True
    everything = b"".join(api.call("GET", p)[1] for p in ("/api/keys", "/api/state", "/api/settings", "/api/health"))
    assert b"SECRETSECRET" not in everything
    assert api.json("DELETE", "/api/keys/openai")[0] == 200 and api.json("GET", "/api/keys")[1]["keys"]["openai"] is False
    assert api.json("PUT", "/api/keys/bogus", {"value": "x"})[0] == 400


def test_settings_refuse_credentials(api):
    status, body = api.json("PUT", "/api/settings", {"values": {"model": "sk-abcdefghijklmnopqrstuvwxyz"}})
    assert status == 400 and "credential" in body["error"]
    assert api.json("PUT", "/api/settings", {"values": {"model": "qwen"}})[0] == 200
    assert api.json("GET", "/api/settings")[1]["model"] == "qwen"


def test_internal_errors_do_not_leak_details(repo, monkeypatch):
    a = Api(repo, Scripted([plan()]))
    try:
        monkeypatch.setattr(a.server.service, "state", lambda: 1 / 0)
        status, body = a.json("GET", "/api/state")
        assert status == 500 and body["error"] == "internal error" and "Zero" not in str(body)
    finally:
        a.close()


def test_second_server_cannot_share_the_port(api, repo):
    from ..server.app import build
    with pytest.raises(OSError):
        build(repo, TOKEN, api.port)


def test_not_reachable_on_other_interfaces(api):
    addrs = {i[4][0] for i in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)} - {"127.0.0.1", "127.0.1.1"}
    for ip in addrs:
        with pytest.raises(OSError), socket.create_connection((ip, api.port), timeout=2):
            pass
