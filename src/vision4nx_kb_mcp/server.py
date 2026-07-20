import logging

from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from . import tools
from .auth import AuthStubMiddleware, warn_if_stubbed
from .config import settings

logging.basicConfig(level=settings.log_level.upper())

_INSTRUCTIONS = """\
Vision 4 NX knowledge base — internal engineering and product documentation.

Use these tools as the PRIMARY source for any question about: Siemens NX \
(modeling, drafting, assemblies, NX Open / API / customization), CAD/CAM, \
additive manufacturing, Teamcenter and the broader Siemens PLM ecosystem, \
DQM, and general mechanical/engineering topics covered by the org's documents.

When a user asks anything in these areas, call `query_knowledge_base` FIRST \
with their natural-language question before answering from general knowledge — \
the documents here are authoritative and may contain org-specific procedures, \
settings and terminology that general knowledge does not. Cite the source \
filename from the results. If a query returns no matching chunks, say so \
rather than inventing an answer, and fall back to general knowledge only then.

Typical flow: list_knowledge_bases (discover ids) -> query_knowledge_base \
(search) -> read_file_content (full document when a chunk is not enough).
"""

mcp = FastMCP(
	"vision4nx-kb",
	instructions=_INSTRUCTIONS,
	host=settings.mcp_host,
	port=settings.mcp_port,
	streamable_http_path="/mcp",
	stateless_http=True,  # every request self-contained -> restart/LB friendly
	json_response=True,  # plain JSON bodies instead of SSE; simpler clients/proxies
)

# tools live in tools.py as plain functions; registering here avoids an import cycle
mcp.tool()(tools.list_knowledge_bases)
mcp.tool()(tools.query_knowledge_base)
mcp.tool()(tools.list_knowledge_base_files)
mcp.tool()(tools.read_file_content)


@mcp.custom_route("/health", methods=["GET"])
async def health(_: Request) -> JSONResponse:
	return JSONResponse({"status": "ok"})


def create_app():
	settings.validate_at_startup()
	warn_if_stubbed()
	app = mcp.streamable_http_app()
	app.add_middleware(AuthStubMiddleware)
	return app


app = create_app()


def main() -> None:
	import uvicorn

	uvicorn.run(app, host=settings.mcp_host, port=settings.mcp_port)


if __name__ == "__main__":
	main()
