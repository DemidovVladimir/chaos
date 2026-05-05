# `market-comp-mcp` — free, derived from the relay's own data

A free MCP that returns pricing comparables for cars, computed from
NIP-99 listings already on configured relays. **No external data, no
scraping, no custody.** The data is on the network already; this MCP
just queries it and computes statistics.

## What it does

Given a vehicle description (make / model / year-range / mileage-band /
region), return:

- **Sample size** — how many comparables were used
- **Median asking price** in the requested currency
- **Range** (10th, 25th, 50th, 75th, 90th percentiles)
- **Recency-weighted median** — fresher listings count more
- **Trend** — week-over-week direction
- **Currency hints** — if the comp set includes multiple currencies,
  conversion summaries

The MCP queries Nostr relays directly (read-only). It doesn't store
anything; results are computed per-request and optionally cached for
a few minutes.

## Why this is the right second free MCP

1. **The data already exists** on the network. No new central
   database.
2. **Better with scale** — every listing improves the comp quality
   for everyone.
3. **No API costs** — just relay queries.
4. **Cross-vertical** — same MCP works for real estate, watches, etc.
5. **Strengthens seeking-cars rubric** — needs market comps to detect
   price-bait scams (price too low) and overpriced listings.

## MCP tool surface

```json
{
  "name": "market_comp",
  "description": "Compute pricing comparables for a vehicle description from NIP-99 listings on the configured Nostr relays. No external data sources.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "make":            {"type": "string"},
      "model":           {"type": "string"},
      "year_min":        {"type": "integer"},
      "year_max":        {"type": "integer"},
      "mileage_band_in": {"type": "array", "items": {"type": "string"}},
      "region_pattern":  {"type": "string"},
      "currency":        {"type": "string"},
      "max_age_days":    {"type": "integer", "default": 60},
      "relays":          {"type": "array", "items": {"type": "string"}}
    },
    "required": ["make", "model"]
  }
}
```

Returns:

```json
{
  "sample_size": 47,
  "currency": "EUR",
  "median": 14500,
  "percentiles": {"p10": 11000, "p25": 12500, "p50": 14500, "p75": 16500, "p90": 18000},
  "recency_weighted_median": 14200,
  "weekly_trend": -0.012,
  "currency_breakdown": {"EUR": 41, "USD": 4, "CZK": 2},
  "stale_warning": false,
  "low_sample_warning": false,
  "relays_queried": [
    "wss://relay.your-domain.app",
    "wss://relay.damus.io",
    "wss://nos.lol"
  ]
}
```

## Edge cases

- **Sample size < 5**: return `low_sample_warning: true`. Seeking agent-cars
  skill warns the user.
- **No comps**: return `sample_size: 0`; skill falls back to a
  different rubric.
- **Currency mix**: compute median in each represented currency, FX-
  cross-reference (ECB-published rates, bundled).
- **Outliers**: trim 5% from each end before computing the recency-
  weighted median.

## Pricing

**Free.** Costs are limited to relay query bandwidth and small
in-memory aggregation. No marginal cost per call.

## Implementation outline

```
market-comp-mcp/
├── pyproject.toml
├── server.py
├── relay_client.py
├── stats.py                  percentile + recency weighting
├── fx.py                     ECB rate snapshot, weekly refresh
└── cache.py                  5-minute in-memory cache
```

~200 lines of Python.

## Strategic role

The market-comp MCP is the lever for the seeking-cars rubric. It feeds
the price-too-high / price-too-low detection. Without it, the skill
has to guess. With it, the skill flags listings that are 15%+ off
median in either direction.

Combined with `reverse-image-mcp` and `vin-decoder-mcp`, the seeking agent-
cars skill has three independent fraud-detection signals, all local,
none requiring third-party data.
