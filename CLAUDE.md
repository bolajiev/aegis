# CLAUDE.md — Esu (Mantle Research Agent)

Repo-level instructions. These stay true for **every** task in this project. Read `SPEC.md` for the full build plan; this file is the always-on guardrail.

---

## What this is
Esu is a Telegram research agent for the **Mantle Research Challenge (Track 2)**. It answers onchain-finance questions about the Mantle ecosystem (RWAs, tokenized equities, DeFi, prediction markets) with **data-backed, sourced** answers. Claude does intent classification + synthesis; a skills layer does data retrieval from DefiLlama / CoinGecko / Mantle RPC.

Judged on: **quality, accuracy, originality, depth.** Optimize every decision for a clean, accurate live demo.

---

## TWO HARD RULES (never violate, in any phase)

1. **Greetings never trigger research.** Every retrieval path sits behind the intent gate (`pipeline/intent.py`). A rules pass catches `hi/gm/thanks/etc.` and returns SMALLTALK with **zero** API calls and **zero** model calls. If you add a new entry point, it must route through the gate first.

2. **Raw JSON / tool output never reaches the user.** Skills return typed `SkillResult` (pydantic) objects. Claude is instructed to emit prose only. A pre-send guard strips/rejects any reply containing JSON, code fences, or `key: value` dumps. Never string-concatenate tool data into a reply.

A third rule that matters just as much: **never fabricate data.** If a skill can't get a number, it returns `ok=False` and the answer says "data unavailable." Inventing figures fails the accuracy criterion.

---

## Stack & conventions
- Python 3.11+, **aiogram 3.x** (modern Router/Dispatcher API — not 2.x), **anthropic** SDK, **httpx** (async), **pydantic v2**, **pydantic-settings**.
- Models: intent → `claude-haiku-4-5-20251001`; synthesis → `claude-sonnet-4-6`.
- All external calls are async (`httpx.AsyncClient`). Research lane fans out with `asyncio.gather`.
- All skill I/O is typed. No untyped dicts crossing layer boundaries except inside `SkillResult.data`.
- Every `SkillResult` carries `source` + `fetched_at` (UTC). These become the inline `(source, date)` citations.
- Never log secrets. `AGENT_PRIVATE_KEY` and `ANTHROPIC_API_KEY` must never appear in logs or error messages.

---

## Commands
```bash
# install
pip install -r requirements.txt        # or: uv pip install -r requirements.txt
# run
python bot.py
# test
pytest -q
```
Keep these working after every phase. The bot must run and be demoable at the end of each phase in SPEC.md §9.

---

## Tasks you (Claude Code) own — do these, don't ask the user

- **Before Phase 6 (SKILL.md mirrors):** clone `https://github.com/mantle-xyz/mantle-skills` and the Agent Scaffold (`https://github.com/mantle-xyz/mantle-agent-scaffold` / its docs site), read the READMEs, and replicate **one** official skill's exact manifest format. Do not guess the SKILL.md shape — copy theirs.
- **Before Phase 5 (ERC-8004):** verify the live IdentityRegistry ABI and address on Mantle mainnet (`0x8004A169FB4a3325136EB29fA0ceB6D2e539a432`) against mantlescan before writing any registration code. Confirm the function signature for registration and the agent-ID return.
- **For each skill:** verify the actual API response shape with a real call before writing the parser. APIs drift — don't assume field names.

If a referenced repo/endpoint can't be reached, say so and stub the module with a clear `TODO`, rather than inventing the interface.

---

## Build order
Follow SPEC.md §9 phases 1→6 in sequence. Each phase ends in a runnable bot. Do not jump ahead or build multiple phases in one pass. After each phase, run the relevant acceptance tests from SPEC.md §10.

## Don't
- Don't use aiogram 2.x syntax.
- Don't add retrieval anywhere outside a skill.
- Don't let Claude free-tool-call its way around the intent gate — the gate decides the lane explicitly.
- Don't over-engineer the bonus modules (ERC-8004, x402) before the core 3-skill demo works end to end.
