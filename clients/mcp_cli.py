"""
Thin async wrapper around the official @mantleio/mantle-cli.
Runs `npx @mantleio/mantle-cli <command> --json` as a subprocess.
Falls back to None if CLI unavailable — callers must handle.
"""
import asyncio
import json
import logging
import shutil

logger = logging.getLogger(__name__)

_NPX = shutil.which("npx")
_TIMEOUT = 15  # seconds


async def call(args: list[str]) -> dict | None:
    """Run mantle-cli with given args, return parsed JSON or None on failure."""
    if not _NPX:
        logger.warning("npx not found — mantle-cli unavailable")
        return None
    cmd = [_NPX, "--yes", "@mantleio/mantle-cli", *args, "--json"]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=_TIMEOUT)
        if proc.returncode != 0:
            logger.warning("mantle-cli %s failed: %s", args, stderr.decode()[:200])
            return None
        return json.loads(stdout.decode())
    except asyncio.TimeoutError:
        logger.warning("mantle-cli %s timed out after %ss", args, _TIMEOUT)
        try:
            proc.kill()
        except Exception:
            pass
        return None
    except Exception as exc:
        logger.warning("mantle-cli %s error: %s", args, exc)
        return None
