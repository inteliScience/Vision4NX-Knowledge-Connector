"""Client-facing authentication for the MCP server.

Static bearer tokens: MCP_AUTH_TOKENS (comma-separated, one per customer, as the
Vision4NX Platform licence file carries them in kbConnector.token) and the older
single MCP_AUTH_TOKEN. With no token configured the server stays open and logs
a warning at startup; with tokens, every request except /health must send
"Authorization: Bearer <token>" and gets 401 otherwise. Comparison is constant
time; the principal in scope state carries the token's index, never the token.
"""

import hmac
import json
import logging
from typing import Any

from starlette.datastructures import Headers

from .config import settings

log = logging.getLogger(__name__)

OPEN_PATHS = ("/health",)


def configured_tokens() -> list[str]:
	tokens = [t.strip() for t in settings.mcp_auth_tokens.split(",") if t.strip()]
	if settings.mcp_auth_token.strip():
		tokens.append(settings.mcp_auth_token.strip())
	return tokens


def verify_request(headers: Headers) -> dict[str, Any]:
	"""The principal of a request, or None when a token is required and missing or wrong."""
	tokens = configured_tokens()
	if not tokens:
		return {"sub": "anonymous", "authenticated": False}
	value = headers.get("authorization", "")
	scheme, _, presented = value.partition(" ")
	presented = presented.strip()
	if scheme.lower() != "bearer" or not presented:
		return None
	for index, token in enumerate(tokens):
		if hmac.compare_digest(presented.encode("utf-8"), token.encode("utf-8")):
			return {"sub": f"token-{index + 1}", "authenticated": True}
	return None


class ClientAuthMiddleware:
	"""Pure-ASGI middleware: attaches the principal to scope state or answers 401."""

	def __init__(self, app: Any) -> None:
		self.app = app

	async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
		if scope["type"] == "http" and not scope.get("path", "").startswith(OPEN_PATHS):
			principal = verify_request(Headers(scope=scope))
			if principal is None:
				body = json.dumps({"error": "unauthorized", "detail": "send Authorization: Bearer <token>"}).encode("utf-8")
				await send({"type": "http.response.start", "status": 401, "headers": [
					(b"content-type", b"application/json"),
					(b"content-length", str(len(body)).encode("ascii")),
					(b"www-authenticate", b"Bearer"),
				]})
				await send({"type": "http.response.body", "body": body})
				return
			state = scope.setdefault("state", {})
			state["principal"] = principal
		await self.app(scope, receive, send)


def log_auth_mode() -> None:
	count = len(configured_tokens())
	if count:
		log.info("client auth: %d bearer token(s) configured", count)
	else:
		log.warning("client auth: no MCP_AUTH_TOKENS configured; the server accepts every client")
