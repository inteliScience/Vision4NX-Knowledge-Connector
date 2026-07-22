"""MCP tool implementations.

Plain async functions — registered on the FastMCP instance in server.py to
avoid an import cycle. Docstrings become the tool descriptions the LLM sees.
"""

from typing import Any

from . import vision4nx


async def list_knowledge_bases() -> dict[str, Any]:
	"""List all knowledge bases accessible to the service account.

	Returns each knowledge base's id, name and description. Use the `id` values
	with query_knowledge_base and list_knowledge_base_files.
	"""
	kbs = await vision4nx.list_knowledge_bases()
	return {
		"knowledge_bases": [
			{
				"id": kb.get("id"),
				"name": kb.get("name"),
				"description": kb.get("description"),
			}
			for kb in kbs
		],
		"count": len(kbs),
	}


async def query_knowledge_base(
	query: str, knowledge_base_ids: list[str], k: int = 5
) -> dict[str, Any]:
	"""Search the Vision 4 NX knowledge base for relevant documentation (RAG search).

	Call this FIRST for any question about Siemens NX (modeling, drafting,
	assemblies, NX Open / API / customization), CAD/CAM, additive manufacturing,
	Teamcenter and the wider Siemens PLM ecosystem, DQM, or general mechanical /
	engineering topics — the org's documents are authoritative for these and may
	hold procedures, settings and terminology not in general knowledge. Prefer
	this over answering from memory whenever the question could plausibly be
	covered here.

	Embedding, hybrid search and reranking happen server-side — pass the
	plain natural-language question. `knowledge_base_ids` are the `id` values from
	list_knowledge_bases (one or more; pass every relevant id to search broadly).
	`k` is the max number of chunks returned. Each result contains the chunk text,
	source filename and file_id (usable with read_file_content for the full
	document). Cite the source filename when you use a result.
	"""
	data = await vision4nx.query_collection(knowledge_base_ids, query, k)

	# response is ChromaDB-style nested lists: one inner list per query (we send one)
	documents = (data.get("documents") or [[]])[0]
	metadatas = (data.get("metadatas") or [[]])[0]
	distances = (data.get("distances") or [[]])[0]

	results = []
	for i, doc in enumerate(documents):
		meta = metadatas[i] if i < len(metadatas) else {}
		meta = meta or {}
		result: dict[str, Any] = {
			"content": doc,
			"source": meta.get("name") or meta.get("source"),
			"file_id": meta.get("file_id"),
		}
		if meta.get("page") is not None:
			result["page"] = meta["page"]
		if i < len(distances) and distances[i] is not None:
			result["relevance"] = round(distances[i], 4)
		results.append(result)

	if not results:
		return {
			"results": [],
			"result_count": 0,
			"note": (
				"No matching chunks found. The knowledge base(s) may be empty or the "
				"ids may be wrong — check them with list_knowledge_bases."
			),
		}
	return {"results": results, "result_count": len(results)}


async def list_knowledge_base_files(knowledge_base_id: str) -> dict[str, Any]:
	"""List the files inside one knowledge base.

	`knowledge_base_id` is an `id` from list_knowledge_bases. Returns file ids,
	names and metadata; use a file's `id` with read_file_content.
	"""
	kb = await vision4nx.get_knowledge_base(knowledge_base_id)
	raw_files = await vision4nx.list_kb_files(knowledge_base_id)
	files = []
	for f in raw_files:
		meta = f.get("meta") or {}
		files.append(
			{
				"id": f.get("id"),
				"name": f.get("filename") or meta.get("name"),  # top-level filename in this fork
				"size": meta.get("size"),
				"content_type": meta.get("content_type"),
				"updated_at": f.get("updated_at"),
			}
		)
	return {
		"knowledge_base": {
			"id": kb.get("id"),
			"name": kb.get("name"),
			"description": kb.get("description"),
		},
		"files": files,
		"file_count": len(files),
	}


async def read_file_content(file_id: str, max_chars: int = 50000) -> dict[str, Any]:
	"""Read the full extracted text content of a file by its id.

	`file_id` comes from list_knowledge_base_files or from query results.
	Content longer than `max_chars` is truncated (truncated=true); call again
	with a larger max_chars if you need the rest.
	"""
	data = await vision4nx.get_file_content(file_id)
	content = data.get("content") or ""
	truncated = len(content) > max_chars
	return {
		"content": content[:max_chars],
		"truncated": truncated,
		"total_chars": len(content),
	}
