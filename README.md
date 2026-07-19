# vision4nx-kb-mcp

MCP server (streamable HTTP) that exposes the **Vision 4 NX / Open WebUI knowledge base** to any MCP client (Claude Code, Claude Desktop, Open WebUI's own MCP client support, ...).

It is a thin wrapper over the Open WebUI REST API — embedding, hybrid search and reranking all happen **inside Open WebUI**, so this server needs no vector-DB access and no embedding model.

> ⚠️ **CLIENT AUTH IS STUBBED.** Every request to this MCP server is accepted.
> The seam for real auth is `src/vision4nx_kb_mcp/auth.py` (`verify_request()`).
> Do not expose this server beyond a trusted network until that is implemented.

## Tools

| Tool | What it does | Open WebUI endpoint |
|---|---|---|
| `list_knowledge_bases()` | List accessible KBs (id, name, description) | `GET /api/v1/knowledge/` (paginated) |
| `query_knowledge_base(query, knowledge_base_ids, k=5)` | RAG vector search; returns relevant chunks with source file info | `POST /api/v1/retrieval/query/collection` |
| `list_knowledge_base_files(knowledge_base_id)` | Files inside one KB | `GET /api/v1/knowledge/{id}` |
| `read_file_content(file_id, max_chars=50000)` | Full extracted text of a file | `GET /api/v1/files/{id}/data/content` |

## Setup

### 1. Get an Open WebUI API key

In Open WebUI: **Settings → Account → API Keys → Create new key** (`sk-...`).

Requirements on the Open WebUI side:
- `ENABLE_API_KEYS` must be enabled (Admin Settings → General).
- The user needs the `features.api_keys` permission.
- If you get **403** errors: `ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS` is on and the endpoints above are missing from `API_KEYS_ALLOWED_ENDPOINTS`.
- **404** on existing resources usually means the API-key user has no read access to that knowledge base (grant access in the KB's sharing settings).

The MCP server acts with this single service key — all clients share that user's KB permissions.

### 2. Configure

```bash
cp .env.example .env   # set OPENWEBUI_URL and OPENWEBUI_API_KEY
```

### 3. Run

**Docker (recommended):**
```bash
docker compose up -d --build
```

**Plain Python (>=3.11):**
```bash
python3.12 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/vision4nx-kb-mcp
# or: .venv/bin/uvicorn vision4nx_kb_mcp.server:app --host 0.0.0.0 --port 8600
```

Health check: `curl http://localhost:8600/health`
MCP endpoint: `http://localhost:8600/mcp`

## Connecting clients

**Claude Code:**
```bash
claude mcp add --transport http vision4nx-kb http://localhost:8600/mcp
```

**Open WebUI itself** (use the KB tools from chats): Admin Settings → External Tools → add a tool server of type **MCP** with URL `http://localhost:8600/mcp` (from inside the compose stack: the container-network URL).

**MCP Inspector** (debugging):
```bash
npx @modelcontextprotocol/inspector
# transport: "Streamable HTTP", URL: http://localhost:8600/mcp
```

## Deploying next to the Vision 4 NX stack

Uncomment the `networks` block in `docker-compose.yaml`, verify the network name (`docker network ls`), and point `OPENWEBUI_URL` at the app container (`http://vision4nx:8080`). Optionally drop the published port and proxy `/mcp` through the existing nginx instead — but only after implementing real client auth.

## Environment variables

| Var | Default | Purpose |
|---|---|---|
| `OPENWEBUI_URL` | — (required) | Base URL of the Open WebUI instance |
| `OPENWEBUI_API_KEY` | — (required) | Service API key (`sk-...`) |
| `MCP_HOST` / `MCP_PORT` | `0.0.0.0` / `8600` | Server bind |
| `MCP_AUTH_TOKEN` | empty | Reserved for future client auth — currently ignored |
| `LOG_LEVEL` | `INFO` | Logging level |

## Tests

Opt-in e2e test against a running server:
```bash
pip install -e '.[dev]'
MCP_SERVER_URL=http://localhost:8600/mcp pytest tests/test_e2e.py
```

## Compatibility

Built against **Open WebUI 0.8.5** (the Vision 4 NX fork), which paginates `GET /api/v1/knowledge/` and pins `mcp==1.26.0`. The paginated-list handling falls back to the upstream unpaginated shape automatically.
