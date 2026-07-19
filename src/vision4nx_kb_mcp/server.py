import logging

from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from . import tools
from .auth import AuthStubMiddleware, warn_if_stubbed
from .config import settings

logging.basicConfig(level=settings.log_level.upper())

mcp = FastMCP(
	"vision4nx-kb",
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
