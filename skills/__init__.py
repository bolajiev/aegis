# Register all skills at import time.
# Import order doesn't matter — each module calls register() at module level.

from skills import (  # noqa: F401
    crypto_price,
    news,
    web_search,
    fetch_url,
    cross_chain,
)

from skills.mantle import (  # noqa: F401
    rwa_tvl,
    defi,
    equity,
    identity,
    chain,
    token_prices,
    portfolio,
    defi_markets,
    risk,
)
