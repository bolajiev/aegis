"""Mantle chain stats — gas, block, chain health. Uses mantle-cli, falls back to RPC."""
import asyncio
import logging
from datetime import datetime, timezone

from clients.mcp_cli import call as mcp_call
from clients.mantle import get_gas_price_gwei, get_latest_block, get_mnt_balance
from skills.base import SkillResult, register

logger = logging.getLogger(__name__)


class MantleChainSkill:
    name = "mantle-chain"

    async def run(self, query: str) -> SkillResult:
        address = None
        q = query.strip()
        if q.startswith("0x") and len(q) >= 40:
            address = q

        try:
            # Try mantle-cli first for chain status
            status_data = None
            info_data = None
            status_task = mcp_call(["chain", "status"])
            info_task   = mcp_call(["chain", "info"])
            status_data, info_data = await asyncio.gather(status_task, info_task)
        except Exception:
            pass

        result: dict = {
            "chain": "Mantle",
            "chain_id": 5000,
            "native_token": "MNT",
            "explorer": "https://mantlescan.xyz",
        }

        if status_data and isinstance(status_data, dict):
            result.update({
                "block_number": status_data.get("blockNumber"),
                "gas_price_gwei": status_data.get("gasPrice"),
                "timestamp": status_data.get("timestamp"),
            })
        else:
            # Fallback to direct RPC
            try:
                gas, block = await asyncio.gather(get_gas_price_gwei(), get_latest_block())
                result.update({
                    "block_number": block.get("number"),
                    "gas_price_gwei": gas,
                    "block_tx_count": block.get("tx_count"),
                    "base_fee_gwei": block.get("base_fee_gwei"),
                })
            except Exception as exc:
                logger.warning("Chain RPC fallback failed: %s", exc)

        if info_data and isinstance(info_data, dict):
            result.update({
                "wrapped_mnt": info_data.get("wrapped_mnt"),
                "rpc_url": info_data.get("rpc_url"),
            })

        if address:
            # Try mantle-cli for balance
            bal_data = await mcp_call(["account", "balance", address])
            if bal_data and isinstance(bal_data, dict):
                result["wallet_balance"] = {
                    "address": address,
                    "mnt_balance": bal_data.get("balance") or bal_data.get("formatted"),
                    "mnt_balance_wei": bal_data.get("balanceWei"),
                }
            else:
                try:
                    mnt_bal = await get_mnt_balance(address)
                    result["wallet_balance"] = {
                        "address": address,
                        "mnt_balance": mnt_bal,
                    }
                except Exception as exc:
                    result["wallet_balance"] = {"error": str(exc)}

        return SkillResult(
            skill=self.name,
            source="Mantle RPC",
            source_url="https://mantlescan.xyz",
            fetched_at=datetime.now(timezone.utc),
            data=result,
        )


register(MantleChainSkill())
