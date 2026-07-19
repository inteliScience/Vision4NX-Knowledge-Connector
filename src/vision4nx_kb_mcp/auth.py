"""Client-facing authentication for the MCP server.

!!! AUTH IS CURRENTLY STUBBED — EVERY REQUEST IS ACCEPTED !!!

This module is the single seam where real authentication goes later.
Implement verify_request() (e.g. static bearer token via MCP_AUTH_TOKEN,
JWT/OIDC validation, or per-user Open WebUI key passthrough) and reject
unauthenticated requests with a 401 instead of passing through.

Do NOT expose this server beyond a trusted network until that is done.
"""

import logging
from typing import Any

from starlette.datastructures import Headers

log = logging.getLogger(__name__)


async def verify_request(headers: Headers) -> dict[str, Any]:
	# TODO(auth): validate headers.get("authorization") against MCP_AUTH_TOKEN
	# (settings.mcp_auth_token) or a JWT/OIDC provider; raise/return 401 on failure.
	return {"sub": "anonymous", "authenticated": False}


class AuthStubMiddleware:
	"""Pure-ASGI middleware; permissive placeholder for real auth."""

	def __init__(self, app: Any) -> None:
		self.app = app

	async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
		if scope["type"] == "http":
			principal = await verify_request(Headers(scope=scope))
			state = scope.setdefault("state", {})
			state["principal"] = principal
		await self.app(scope, receive, send)


def warn_if_stubbed() -> None:
	log.warning(
		"=" * 72
		+ "\nCLIENT AUTH IS STUBBED (permissive) — every MCP request is accepted."
		"\nImplement verify_request() in auth.py before exposing this server"
		"\nbeyond a trusted network.\n" + "=" * 72
	)
