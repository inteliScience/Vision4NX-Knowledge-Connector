"""Thin async client for the Vision 4 NX REST API.

All heavy lifting (embedding, hybrid search, reranking) happens server-side in
Vision 4 NX — this module only wraps the four endpoints the MCP tools need.
"""

from typing import Any

import httpx

from .config import settings


class Vision4NXError(Exception):
	"""Raised for any failed Vision 4 NX request; message is shown to the MCP client."""


_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
	global _client
	if _client is None:
		_client = httpx.AsyncClient(
			base_url=settings.vision4nx_url,
			headers={"Authorization": f"Bearer {settings.vision4nx_api_key}"},
			timeout=60.0,  # hybrid search + rerank on large KBs can be slow
		)
	return _client


async def _request(method: str, path: str, **kwargs: Any) -> Any:
	try:
		response = await get_client().request(method, path, **kwargs)
	except httpx.ConnectError as e:
		raise Vision4NXError(f"Cannot reach Vision 4 NX at {settings.vision4nx_url}: {e}") from e
	except httpx.TimeoutException as e:
		raise Vision4NXError(f"Vision 4 NX request timed out ({method} {path}): {e}") from e

	if response.status_code == 401:
		raise Vision4NXError(
			"Access token rejected (401). Verify VISION4NX_API_KEY, or request a "
			"valid token from Inteliscience (info@inteliscience.net)."
		)
	if response.status_code == 403:
		raise Vision4NXError(
			f"Access denied (403) for {path}. The access token may lack permission "
			"for this resource — contact Inteliscience (info@inteliscience.net)."
		)
	if response.status_code == 404:
		raise Vision4NXError(
			f"Not found: {path}. This can also mean the access token has no read "
			"access to the resource — contact Inteliscience (info@inteliscience.net)."
		)
	if response.is_error:
		detail = response.text[:500]
		raise Vision4NXError(f"Vision 4 NX error {response.status_code} for {path}: {detail}")
	try:
		return response.json()
	except ValueError as e:
		raise Vision4NXError(
			f"Vision 4 NX returned non-JSON for {path} — is VISION4NX_URL "
			f"({settings.vision4nx_url}) actually a Vision 4 NX instance?"
		) from e


async def list_knowledge_bases() -> list[dict[str, Any]]:
	# the API paginates GET /api/v1/knowledge/ at 30 items/page ({items, total})
	items: list[dict[str, Any]] = []
	page = 1
	while True:
		data = await _request("GET", "/api/v1/knowledge/", params={"page": page})
		if isinstance(data, list):  # unpaginated response shape, just in case
			return data
		items.extend(data.get("items") or [])
		total = data.get("total", len(items))
		if len(items) >= total or not data.get("items"):
			return items
		page += 1


async def query_collection(
	collection_names: list[str], query: str, k: int, k_reranker: int
) -> dict[str, Any]:
	# `k` is the candidate pool the server retrieves per collection, `k_reranker` is how
	# many survive reranking. Sending `k` at all overrides the instance's configured
	# TOP_K, so it must be the wide pool value — sending the desired result count here
	# starves the reranker instead of limiting it.
	return await _request(
		"POST",
		"/api/v1/retrieval/query/collection",
		json={
			"collection_names": collection_names,
			"query": query,
			"k": k,
			"k_reranker": k_reranker,
		},
	)


async def get_knowledge_base(knowledge_id: str) -> dict[str, Any]:
	# note: this endpoint's `files` field is null — use list_kb_files for files
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
