"""Wallet portfolio on Mantle — balances + Aave positions via mantle-cli."""
import asyncio
import logging
from datetime import datetime, timezone

from clients.mcp_cli import call as mcp_call
from clients.mantle import get_mnt_balance
from skills.base import SkillResult, register

logger = logging.getLogger(__name__)

_DEFAULT_TOKENS = "MNT,WMNT,USDT,USDC,WETH,mETH,FBTC"


class MantlePortfolioSkill:
    name = "mantle-portfolio"

    async def run(self, query: str) -> SkillResult:
        q = query.strip()
        address = None
        for part in q.split():
            if part.startswith("0x") and len(part) >= 40:
                address = part
                break

        if not address:
            return SkillResult.failure(
                self.name,
                "Mantle RPC",
                "Please provide a wallet address starting with 0x",
            )

        result: dict = {"address": address}

        # Native MNT balance + token balances + Aave positions in parallel
        native_task   = mcp_call(["account", "balance", address])
        tokens_task   = mcp_call(["account", "token-balances", address, "--tokens", _DEFAULT_TOKENS])
        aave_task     = mcp_call(["aave", "positions", "--user", address])

        native, tokens, aave = await asyncio.gather(native_task, tokens_task, aave_task)

        # Native balance
        if native and isinstance(native, dict):
            result["mnt_balance"] = native.get("balance") or native.get("formatted") or native.get("amount")
        else:
            try:
                result["mnt_balance"] = await get_mnt_balance(address)
            except Exception as exc:
                result["mnt_balance_error"] = str(exc)

        # ERC-20 balances
        if tokens and isinstance(tokens, (dict, list)):
            result["token_balances"] = tokens

        # Aave lending positions
        if aave and isinstance(aave, (dict, list)):
            result["aave_positions"] = aave

        explorer = f"https://mantlescan.xyz/address/{address}"
        result["explorer"] = explorer

        return SkillResult(
            skill=self.name,
            source="Mantle RPC / mantle-cli",
            fetched_at=datetime.now(timezone.utc),
            data=result,
        )


register(MantlePortfolioSkill())
