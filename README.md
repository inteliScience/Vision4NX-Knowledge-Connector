# vision4nx-kb-mcp

MCP server (streamable HTTP) that exposes the **Vision 4 NX knowledge base** to any MCP client (Claude Code, Claude Desktop, and other MCP-capable clients).

It is a thin wrapper over the Vision 4 NX REST API — embedding, hybrid search and reranking all happen **server-side**, so this server needs no vector-DB access and no embedding model.

## Tools

| Tool | What it does | Vision 4 NX endpoint |
|---|---|---|
| `list_knowledge_bases()` | List accessible KBs (id, name, description) | `GET /api/v1/knowledge/` (paginated) |
| `query_knowledge_base(query, knowledge_base_ids, max_results=8)` | RAG hybrid search; returns reranked chunks with source file info | `POST /api/v1/retrieval/query/collection` |
| `list_knowledge_base_files(knowledge_base_id)` | Files inside one KB | `GET /api/v1/knowledge/{id}` |
| `read_file_content(file_id, max_chars=50000)` | Full extracted text of a file | `GET /api/v1/files/{id}/data/content` |

## Setup

### 0. Prerequisites

Either of:

- **Docker** — Docker Desktop (macOS/Windows) or Docker Engine (Linux) with
  Compose v2. Check with `docker compose version`; if only `docker-compose`
  (with a hyphen) works, the install is too old — upgrade, or substitute
  `docker-compose` in the commands below.
- **Python 3.11+** if you'd rather run it without Docker.

### 1. Get the code

```bash
git clone https://github.com/inteliScience/Vision4NX-Knowledge-Connector.git
cd Vision4NX-Knowledge-Connector
```

Every command in this README is run from that directory — it's the one holding
`docker-compose.yaml`.

### 2. Get your access credentials

The `VISION4NX_URL` and `VISION4NX_API_KEY` for the Vision 4 NX instance are
issued on request. Contact the Inteliscience team at **info@inteliscience.net**
to obtain them.

The MCP server acts with this single service key — all clients share the KB
permissions granted to it.

If tools return **403** or **404** errors, the access token may be missing
permissions for a knowledge base — contact Inteliscience to have it adjusted.

### 3. Configure

```bash
cp .env.example .env   # set VISION4NX_URL and VISION4NX_API_KEY (from Inteliscience)
```

Both are required. The server refuses to start without them, and Compose won't
even build if `.env` is missing entirely.

### 4. Run

**Docker (recommended)** — from the repo root:
```bash
docker compose up -d --build
docker compose logs -f    # first run: confirm it actually came up
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

### Troubleshooting

`docker compose up -d` reports success even when the container crashes a second
later, so check the logs before anything else:

```bash
docker compose ps        # STATUS "Restarting" = it's crash-looping
docker compose logs -f
```

| Symptom | Cause |
|---|---|
| `env file .../.env not found` | Step 3 was skipped — `cp .env.example .env` |
| Container restarts forever, log says `Missing required environment variables: ...` | `VISION4NX_URL` / `VISION4NX_API_KEY` are empty in `.env`. `restart: unless-stopped` retries the crash, so `up -d` looks like it worked |
| `docker: 'compose' is not a docker command` | Compose v1 — use `docker-compose up -d --build` or upgrade Docker |
| Connection refused on `localhost:8600` | Server isn't up; see the two rows above |
| Tools return 403 / 404 | Token lacks permissions for that KB — contact Inteliscience |

After editing `.env`, restart to pick it up: `docker compose up -d`
(`--build` is only needed when the code changes).

## Connecting clients

This server speaks **streamable HTTP** at `http://localhost:8600/mcp`. Clients
that support HTTP/remote MCP connect to that URL directly; stdio-only clients
need the `mcp-remote` bridge (shown below). No auth token is required — client
auth is not enforced by this server.

**Claude Code:**
```bash
claude mcp add --transport http vision4nx-kb http://localhost:8600/mcp
```

**Claude Desktop:** two ways, depending on your version.

- *Custom connector (if available):* Settings → Connectors → **Add custom
  connector**, name it `Vision 4 NX KB`, URL `http://localhost:8600/mcp`, save
  and enable.
- *Config file (works everywhere, needs Node.js):* the desktop config only
  launches stdio commands, so bridge the HTTP endpoint with `mcp-remote`. Edit
  `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or
  `%APPDATA%\Claude\claude_desktop_config.json` (Windows):
  ```json
  {
    "mcpServers": {
      "vision4nx-kb": {
        "command": "npx",
        "args": ["-y", "mcp-remote", "http://localhost:8600/mcp"]
      }
    }
  }
  ```
  Then fully quit and reopen Claude Desktop (Cmd+Q / quit from the tray — closing
  the window is not enough).

**Vision 4 NX itself** (use the KB tools from chats): Admin Settings → External Tools → add a tool server of type **MCP** with URL `http://localhost:8600/mcp` (from inside the compose stack: the container-network URL).

**Any other MCP client:** point it at `http://localhost:8600/mcp` with transport
**Streamable HTTP**. If the client only supports stdio, wrap it the same way
Claude Desktop's config file does:
`npx -y mcp-remote http://localhost:8600/mcp`.

**MCP Inspector** (debugging):
```bash
npx @modelcontextprotocol/inspector
# transport: "Streamable HTTP", URL: http://localhost:8600/mcp
```

## Deploying next to the Vision 4 NX stack

Uncomment the `networks` block in `docker-compose.yaml`, verify the network name (`docker network ls`), and point `VISION4NX_URL` at the app container (`http://vision4nx:8080`). Optionally drop the published port and proxy `/mcp` through the existing nginx instead.

## Environment variables

| Var | Default | Purpose |
|---|---|---|
| `VISION4NX_URL` | — (required) | Base URL of the Vision 4 NX instance (issued by Inteliscience) |
| `VISION4NX_API_KEY` | — (required) | Service access token (issued by Inteliscience — info@inteliscience.net) |
| `RETRIEVAL_CANDIDATE_POOL` | `40` | Chunks retrieved per collection before reranking. Sent as the API's `k`; `max_results` is sent as `k_reranker` and bounds what comes back. Only bites on instances with hybrid search + a reranker configured |
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

Built against the Vision 4 NX backend, which paginates `GET /api/v1/knowledge/` and pins `mcp==1.26.0`. The paginated-list handling falls back to an unpaginated response shape automatically.
