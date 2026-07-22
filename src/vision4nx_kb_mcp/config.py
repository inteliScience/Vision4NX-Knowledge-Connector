import logging

from pydantic_settings import BaseSettings, SettingsConfigDict

log = logging.getLogger(__name__)


class Settings(BaseSettings):
	model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

	# Vision 4 NX instance the tools talk to
	vision4nx_url: str = ""  # base URL — required at startup
	vision4nx_api_key: str = ""  # service access token — required at startup

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
				("VISION4NX_URL", self.vision4nx_url),
				("VISION4NX_API_KEY", self.vision4nx_api_key),
			)
			if not value.strip()
		]
		if missing:
			raise SystemExit(f"Missing required environment variables: {', '.join(missing)}")
		self.vision4nx_url = self.vision4nx_url.rstrip("/")


settings = Settings()
