"""Opt-in e2e test against a RUNNING MCP server (which itself needs a running
Open WebUI instance with a valid API key).

    MCP_SERVER_URL=http://localhost:8600/mcp pytest tests/test_e2e.py
"""

import os

import pytest

MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL")

pytestmark = pytest.mark.skipif(
	not MCP_SERVER_URL, reason="set MCP_SERVER_URL to run the e2e test"
)


@pytest.mark.asyncio
async def test_list_tools_and_list_knowledge_bases():
	from mcp import ClientSession
	from mcp.client.streamable_http import streamablehttp_client

	async with streamablehttp_client(MCP_SERVER_URL) as (read, write, _):
		async with ClientSession(read, write) as session:
			await session.initialize()

			tools = await session.list_tools()
			names = {t.name for t in tools.tools}
			assert names == {
				"list_knowledge_bases",
				"query_knowledge_base",
				"list_knowledge_base_files",
				"read_file_content",
			}

			result = await session.call_tool("list_knowledge_bases", {})
			assert not result.isError
