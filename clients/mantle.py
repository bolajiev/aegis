"""
Mantle RPC + mantlescan (Etherscan-compatible) client.

RPC calls need no key. Mantlescan stats require MANTLESCAN_API_KEY (optional).
"""
import httpx
from config import settings

from clients._retry import get_json

_RPC = settings.mantle_rpc_url
_SCAN_BASE = "https://api.etherscan.io/v2/api"
_TIMEOUT = 10.0


async def rpc(method: str, params: list | None = None) -> object:
    payload = {"jsonrpc": "2.0", "method": method, "params": params or [], "id": 1}
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        r = await client.post(_RPC, json=payload)
        r.raise_for_status()
        body = r.json()
    if "error" in body:
        raise RuntimeError(f"RPC error {body['error']}")
    return body["result"]


async def get_gas_price_gwei() -> float:
    raw = await rpc("eth_gasPrice")
    return int(raw, 16) / 1e9


async def get_latest_block() -> dict:
    block = await rpc("eth_getBlockByNumber", ["latest", False])
    return {
        "number": int(block["number"], 16),
        "timestamp": int(block["timestamp"], 16),
        "gas_used": int(block["gasUsed"], 16),
        "gas_limit": int(block["gasLimit"], 16),
        "tx_count": len(block["transactions"]),
        "base_fee_gwei": int(block.get("baseFeePerGas", "0x0"), 16) / 1e9,
    }


async def get_mnt_balance(address: str) -> float:
    """Returns MNT (native) balance for *address* in whole tokens."""
    raw = await rpc("eth_getBalance", [address, "latest"])
    return int(raw, 16) / 1e18


async def get_scan_stats() -> dict | None:
    """Fetch supply + price stats from mantlescan (needs MANTLESCAN_API_KEY)."""
    key = settings.mantlescan_api_key
    if not key:
        return None
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        supply = await get_json(
            client, _SCAN_BASE,
            params={"chainid": "5000", "module": "stats", "action": "ethsupply", "apikey": key},
        )
        price = await get_json(
            client, _SCAN_BASE,
            params={"chainid": "5000", "module": "stats", "action": "ethprice", "apikey": key},
        )
    if supply.get("status") != "1" or price.get("status") != "1":
        return None
    return {
        "circulating_supply": int(supply["result"]) / 1e18,
        "price_usd": float(price["result"]["ethusd"]),
        "price_btc": float(price["result"]["ethbtc"]),
    }
