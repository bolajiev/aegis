"""
ERC-8004 Agent Registration — run ONCE.

Registers Aegis with the AgentIdentity contract on Mantle mainnet and saves
the resulting token ID to .agent_id.

Usage:
    AGENT_PRIVATE_KEY=0x... python3 register_agent.py

Requires AGENT_PRIVATE_KEY in .env or the environment.
NEVER commit or log the private key.
"""
import asyncio
import base64
import json
import os
import sys
from pathlib import Path

# Load config (will exit if required vars are missing)
from config import settings

REGISTRY = "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432"
CHAIN_ID  = 5000  # Mantle mainnet
AGENT_ID_FILE = Path(__file__).parent / ".agent_id"

# Verified ABI (read from live contract 2026-06-22)
MINIMAL_ABI = [
    {
        "inputs": [{"name": "metadataUrl", "type": "string"}],
        "name": "register",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"name": "tokenId", "type": "uint256"}],
        "name": "tokenURI",
        "outputs": [{"name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"name": "owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "from", "type": "address"},
            {"indexed": True, "name": "to", "type": "address"},
            {"indexed": True, "name": "tokenId", "type": "uint256"},
        ],
        "name": "Transfer",
        "type": "event",
    },
]

TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
ZERO_ADDRESS   = "0x0000000000000000000000000000000000000000"


def _build_metadata_uri() -> str:
    """Encode agent-card.json as a self-contained data URI."""
    card_path = Path(__file__).parent / "skill_manifests" / "esu" / "agent-card.json"
    with open(card_path) as f:
        card = json.load(f)
    encoded = base64.b64encode(json.dumps(card).encode()).decode()
    return f"data:application/json;base64,{encoded}"


def _extract_token_id(receipt) -> int | None:
    """Extract the minted token ID from a registration transaction receipt."""
    for log in receipt["logs"]:
        topics = log.get("topics", [])
        if (
            len(topics) == 4
            and topics[0].lower() == TRANSFER_TOPIC.lower()
            and topics[1].lower() == ("0x" + "0" * 64).lower()
        ):
            return int(topics[3], 16)
    return None


async def main() -> None:
    if not settings.agent_private_key:
        sys.exit(
            "[register_agent] AGENT_PRIVATE_KEY is not set.\n"
            "Add it to .env — never commit or log the key."
        )

    try:
        from web3 import Web3
    except ImportError:
        sys.exit("[register_agent] web3 package not installed. Run: pip install web3")

    w3 = Web3(Web3.HTTPProvider(settings.mantle_rpc_url))
    if not w3.is_connected():
        sys.exit(f"[register_agent] Cannot connect to RPC: {settings.mantle_rpc_url}")

    account = w3.eth.account.from_key(settings.agent_private_key)
    print(f"Agent address : {account.address}")

    contract = w3.eth.contract(
        address=Web3.to_checksum_address(REGISTRY),
        abi=MINIMAL_ABI,
    )

    # Check if already registered
    balance = contract.functions.balanceOf(account.address).call()
    if balance > 0:
        print("Already registered! Checking for saved agent ID…")
        if AGENT_ID_FILE.exists():
            token_id = int(AGENT_ID_FILE.read_text().strip())
            print(f"Agent ID (from .agent_id): {token_id}")
        else:
            print("Agent ID file not found. Re-check transaction history manually.")
        return

    metadata_url = _build_metadata_uri()
    print(f"Metadata URL  : {metadata_url[:80]}…")

    # Estimate gas
    gas_estimate = contract.functions.register(metadata_url).estimate_gas(
        {"from": account.address}
    )
    gas_limit = int(gas_estimate * 1.3)

    nonce = w3.eth.get_transaction_count(account.address)
    gas_price = w3.eth.gas_price

    tx = contract.functions.register(metadata_url).build_transaction(
        {
            "chainId": CHAIN_ID,
            "from": account.address,
            "nonce": nonce,
            "gas": gas_limit,
            "gasPrice": gas_price,
        }
    )

    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"Tx submitted  : {tx_hash.hex()}")
    print("Waiting for confirmation…")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    if receipt["status"] != 1:
        sys.exit(f"[register_agent] Transaction failed: {tx_hash.hex()}")

    token_id = _extract_token_id(receipt)
    if token_id is None:
        sys.exit("[register_agent] Could not extract token ID from receipt — check logs manually.")

    AGENT_ID_FILE.write_text(str(token_id))
    print(f"\n✓ Registered! Aegis's ERC-8004 Agent ID: {token_id}")
    print(f"  Saved to: {AGENT_ID_FILE}")
    print(f"  View on mantlescan: https://mantlescan.xyz/token/{REGISTRY}/instance/{token_id}")


if __name__ == "__main__":
    asyncio.run(main())
