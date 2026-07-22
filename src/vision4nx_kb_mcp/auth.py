"""Client-facing authentication for the MCP server.

verify_request() is the single seam for client authentication. See the
internal developer notes for the current enforcement status and the options
for implementing it (static bearer token via MCP_AUTH_TOKEN, JWT/OIDC
validation, or per-user key passthrough).
"""

import logging
from typing import Any

from starlette.datastructures import Headers

log = logging.getLogger(__name__)


async def verify_request(headers: Headers) -> dict[str, Any]:
	# TODO(auth): validate headers.get("authorization") against settings.mcp_auth_token
	# or a JWT/OIDC provider and return/raise 401 on failure.
	return {"sub": "anonymous", "authenticated": False}


class ClientAuthMiddleware:
	"""Pure-ASGI middleware that attaches the request principal to scope state."""

	def __init__(self, app: Any) -> None:
		self.app = app

	async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
		if scope["type"] == "http":
			principal = await verify_request(Headers(scope=scope))
			state = scope.setdefault("state", {})
			state["principal"] = principal
		await self.app(scope, receive, send)
