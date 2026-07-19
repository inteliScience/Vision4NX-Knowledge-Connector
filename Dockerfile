FROM python:3.12-slim

WORKDIR /app

# install deps first for layer caching, then the project itself
COPY pyproject.toml ./
COPY src/ src/
RUN pip install --no-cache-dir .

RUN useradd -m -u 1001 mcp && chown -R mcp:mcp /app
USER mcp

ENV MCP_HOST=0.0.0.0 \
    MCP_PORT=8600

EXPOSE 8600

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:8600/health')"

CMD ["vision4nx-kb-mcp"]
