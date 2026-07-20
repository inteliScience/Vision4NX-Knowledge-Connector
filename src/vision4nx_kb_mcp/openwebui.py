"""Thin async client for the Open WebUI / Vision 4 NX REST API.

All heavy lifting (embedding, hybrid search, reranking) happens server-side in
Open WebUI — this module only wraps the four endpoints the MCP tools need.
"""

from typing import Any

import httpx

from .config import settings


class OpenWebUIError(Exception):
	"""Raised for any failed Open WebUI request; message is shown to the MCP client."""


_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
	global _client
	if _client is None:
		_client = httpx.AsyncClient(
			base_url=settings.openwebui_url,
			headers={"Authorization": f"Bearer {settings.openwebui_api_key}"},
			timeout=60.0,  # hybrid search + rerank on large KBs can be slow
		)
	return _client


async def _request(method: str, path: str, **kwargs: Any) -> Any:
	try:
		response = await get_client().request(method, path, **kwargs)
	except httpx.ConnectError as e:
		raise OpenWebUIError(f"Cannot reach Open WebUI at {settings.openwebui_url}: {e}") from e
	except httpx.TimeoutException as e:
		raise OpenWebUIError(f"Open WebUI request timed out ({method} {path}): {e}") from e

	if response.status_code == 401:
		raise OpenWebUIError(
			"Open WebUI rejected the service API key (401). "
			"Check OPENWEBUI_API_KEY and that ENABLE_API_KEYS is enabled."
		)
	if response.status_code == 403:
		raise OpenWebUIError(
			f"Access denied (403) for {path}. If API key endpoint restrictions are enabled "
			"(ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS), add this endpoint to API_KEYS_ALLOWED_ENDPOINTS."
		)
	if response.status_code == 404:
		raise OpenWebUIError(
			f"Not found: {path}. Note: Open WebUI also returns 404 when the "
			"service account lacks read access to the resource."
		)
	if response.is_error:
		detail = response.text[:500]
		raise OpenWebUIError(f"Open WebUI error {response.status_code} for {path}: {detail}")
	try:
		return response.json()
	except ValueError as e:
		raise OpenWebUIError(
			f"Open WebUI returned non-JSON for {path} — is OPENWEBUI_URL "
			f"({settings.openwebui_url}) actually an Open WebUI instance?"
		) from e


async def list_knowledge_bases() -> list[dict[str, Any]]:
	# this fork paginates GET /api/v1/knowledge/ at 30 items/page ({items, total})
	items: list[dict[str, Any]] = []
	page = 1
	while True:
		data = await _request("GET", "/api/v1/knowledge/", params={"page": page})
		if isinstance(data, list):  # upstream (unpaginated) response shape, just in case
			return data
		items.extend(data.get("items") or [])
		total = data.get("total", len(items))
		if len(items) >= total or not data.get("items"):
			return items
		page += 1


async def query_collection(collection_names: list[str], query: str, k: int) -> dict[str, Any]:
	return await _request(
		"POST",
		"/api/v1/retrieval/query/collection",
		json={"collection_names": collection_names, "query": query, "k": k},
	)


async def get_knowledge_base(knowledge_id: str) -> dict[str, Any]:
	# note: this endpoint's `files` field is null in the fork — use list_kb_files for files
	return await _request("GET", f"/api/v1/knowledge/{knowledge_id}")


async def list_kb_files(knowledge_id: str) -> list[dict[str, Any]]:
	# GET /api/v1/knowledge/{id}/files is paginated ({items, total}, 30/page)
	items: list[dict[str, Any]] = []
	page = 1
	while True:
		data = await _request(
			"GET", f"/api/v1/knowledge/{knowledge_id}/files", params={"page": page}
		)
		if isinstance(data, list):  # fallback for an unpaginated shape
			return data
		items.extend(data.get("items") or [])
		total = data.get("total", len(items))
		if len(items) >= total or not data.get("items"):
			return items
		page += 1


async def get_file_content(file_id: str) -> dict[str, Any]:
	return await _request("GET", f"/api/v1/files/{file_id}/data/content")
