"""Client auth: open without tokens, 401 without or with a wrong bearer, pass with a right one, /health always open.

Runs without a Vision 4 NX instance:  python -m pytest tests/test_auth.py
"""

import asyncio
import os

os.environ.setdefault("VISION4NX_URL", "https://example.invalid")
os.environ.setdefault("VISION4NX_API_KEY", "service-key-for-tests")

from starlette.datastructures import Headers  # noqa: E402

from vision4nx_kb_mcp import auth  # noqa: E402
from vision4nx_kb_mcp.config import settings  # noqa: E402


def _headers(**kw):
	return Headers({k.replace("_", "-"): v for k, v in kw.items()})


def _run(middleware, path, authorization=None):
	sent = []
	scope = {"type": "http", "path": path, "headers": [(b"authorization", authorization.encode())] if authorization else []}

	async def inner(scope, receive, send):
		await send({"type": "http.response.start", "status": 200, "headers": []})
		await send({"type": "http.response.body", "body": b"ok"})

	async def send(message):
		sent.append(message)

	asyncio.run(middleware.__class__(inner)(scope, None, send))
	return sent[0]["status"], scope.get("state", {}).get("principal")


def test_open_without_tokens(monkeypatch):
	monkeypatch.setattr(settings, "mcp_auth_tokens", "")
	monkeypatch.setattr(settings, "mcp_auth_token", "")
	assert auth.verify_request(_headers()) == {"sub": "anonymous", "authenticated": False}
	status, principal = _run(auth.ClientAuthMiddleware(None), "/mcp")
	assert status == 200 and principal["authenticated"] is False


def test_tokens_required(monkeypatch):
	monkeypatch.setattr(settings, "mcp_auth_tokens", "kunde-a-token, kunde-b-token")
	monkeypatch.setattr(settings, "mcp_auth_token", "")
	assert auth.verify_request(_headers()) is None
	assert auth.verify_request(_headers(authorization="Bearer wrong")) is None
	assert auth.verify_request(_headers(authorization="Basic kunde-a-token")) is None
	assert auth.verify_request(_headers(authorization="Bearer kunde-b-token")) == {"sub": "token-2", "authenticated": True}
	status, _ = _run(auth.ClientAuthMiddleware(None), "/mcp")
	assert status == 401
	status, _ = _run(auth.ClientAuthMiddleware(None), "/mcp", "Bearer nope")
	assert status == 401
	status, principal = _run(auth.ClientAuthMiddleware(None), "/mcp", "Bearer kunde-a-token")
	assert status == 200 and principal == {"sub": "token-1", "authenticated": True}
	status, _ = _run(auth.ClientAuthMiddleware(None), "/health")
	assert status == 200


def test_single_token_form(monkeypatch):
	monkeypatch.setattr(settings, "mcp_auth_tokens", "")
	monkeypatch.setattr(settings, "mcp_auth_token", "legacy")
	assert auth.verify_request(_headers(authorization="bearer legacy")) == {"sub": "token-1", "authenticated": True}
	assert auth.verify_request(_headers(authorization="Bearer other")) is None
