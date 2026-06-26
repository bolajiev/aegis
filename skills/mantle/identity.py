"""ERC-8004 agent identity — reads Aegis's registration from Mantle mainnet."""
import logging
from datetime import datetime, timezone

from clients.mantle import rpc
from config import settings
from skills.base import SkillResult, register

logger = logging.getLogger(__name__)

_REGISTRY_ABI_BALANCEOF = "0x70a08231"  # balanceOf(address)
_REGISTRY_ABI_TOKENURI  = "0xc87b56dd"  # tokenURI(uint256)


def _encode_call(sig: str, address: str) -> str:
    addr_padded = address[2:].zfill(64)
    return sig + addr_padded


def _encode_token_uri(sig: str, token_id: int) -> str:
    token_padded = hex(token_id)[2:].zfill(64)
    return sig + token_padded


class MantleIdentitySkill:
    name = "mantle-identity"

    async def run(self, query: str) -> SkillResult:
        registry = settings.erc8004_identity_registry
        private_key = settings.agent_private_key

        # Derive agent's address from private key if available
        agent_address = None
        if private_key and private_key.startswith("0x"):
            try:
                from eth_account import Account
                acct = Account.from_key(private_key)
                agent_address = acct.address
            except Exception:
                pass

        if not agent_address:
            return SkillResult(
                skill=self.name,
                source="Mantle RPC",
                fetched_at=datetime.now(timezone.utc),
                data={
                    "registered": False,
                    "registry": registry,
                    "note": "No agent wallet configured (AGENT_PRIVATE_KEY not set)",
                    "erc_standard": "ERC-8004",
                    "chain": "Mantle Mainnet (chain ID 5000)",
                },
            )

        try:
            balance_data = _encode_call(_REGISTRY_ABI_BALANCEOF, agent_address)
            balance_raw = await rpc("eth_call", [{"to": registry, "data": balance_data}, "latest"])
            balance = int(balance_raw, 16)

            identity = {
                "registered": balance > 0,
                "agent_address": agent_address,
                "registry": registry,
                "token_count": balance,
                "erc_standard": "ERC-8004",
                "chain": "Mantle Mainnet (chain ID 5000)",
                "explorer": f"https://mantlescan.xyz/address/{agent_address}",
            }

            return SkillResult(
                skill=self.name,
                source="Mantle RPC",
                fetched_at=datetime.now(timezone.utc),
                data=identity,
            )
        except Exception as exc:
            logger.exception("mantle-identity RPC call failed")
            return SkillResult.failure(self.name, "Mantle RPC", str(exc))


register(MantleIdentitySkill())
