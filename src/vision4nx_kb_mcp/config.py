import logging

from pydantic_settings import BaseSettings, SettingsConfigDict

log = logging.getLogger(__name__)


class Settings(BaseSettings):
	model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

	# Open WebUI / Vision 4 NX instance the tools talk to
	openwebui_url: str = ""  # e.g. http://localhost:3000 — required at startup
	openwebui_api_key: str = ""  # user API key (sk-...) — required at startup

	# MCP server bind
	mcp_host: str = "0.0.0.0"
	mcp_port: int = 8600

	# reserved for the future real auth implementation; the stub ignores it
	mcp_auth_token: str = ""

	log_level: str = "INFO"

	def validate_at_startup(self) -> None:
		# fail fast on missing required config instead of erroring on first tool call
		missing = [
			name
			for name, value in (
				("OPENWEBUI_URL", self.openwebui_url),
				("OPENWEBUI_API_KEY", self.openwebui_api_key),
			)
			if not value.strip()
		]
		if missing:
			raise SystemExit(f"Missing required environment variables: {', '.join(missing)}")
		self.openwebui_url = self.openwebui_url.rstrip("/")


settings = Settings()
