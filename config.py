import sys
from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    telegram_bot_token: str
    qwen_api_key: str
    qwen_base_url: str = "https://ws-oauxfmllk3or8gtx.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"

    # Model names — qwen-turbo is fast/cheap (Haiku analog); qwen-plus is quality (Sonnet analog)
    intent_model: str = "qwen-turbo"
    synth_model: str = "qwen-plus"

    coingecko_api_key: str = ""
    mantlescan_api_key: str = ""
    mantle_rpc_url: str = "https://rpc.mantle.xyz"

    # Phase 5 — never log these
    agent_private_key: str = ""
    erc8004_identity_registry: str = "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432"


try:
    settings = Settings()
except ValidationError as exc:
    missing = [e["loc"][0] for e in exc.errors() if e["type"] == "missing"]
    sys.exit(
        f"[config] Missing required environment variables: {', '.join(str(m) for m in missing)}\n"
        "Copy .env.example to .env and fill in TELEGRAM_BOT_TOKEN and QWEN_API_KEY."
    )
