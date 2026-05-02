# Cars NIP-99 tag schema

Conventions for tagging a car listing as a NIP-99 event (`kind: 30402`).
Stable contract; additive changes only.

## Required tags

| Tag | Cardinality | Purpose | Example |
|---|---|---|---|
| `d` | 1 | Addressable item id (uuid v4) | `["d", "8f4a2b1e-6c0d-4f29-9bd3-...]` |
| `title` | 1 | Human-readable title (≤ 200 chars) | `["title", "2018 Mazda 3 hatchback"]` |
| `summary` | 1 | One-line summary (≤ 280 chars) | `["summary", "65k mi, 1 owner, all-services"]` |
| `t` | ≥ 2 | Discovery tags. Always include `t=cars` and `t=<make-lower>` | `["t","cars"], ["t","mazda"]` |
| `price` | 1 | NIP-99 price in `[amount, currency, frequency]` | `["price","15000","EUR",""]` |
| `location` | 1 | Hierarchical region (continent/country/city or geohash) | `["location","EU/CZ/Prague"]` |
| `make` | 1 | Manufacturer, lowercase | `["make","mazda"]` |
| `model` | 1 | Model, lowercase | `["model","3"]` |
| `year` | 1 | Model year, integer string | `["year","2018"]` |
| `body_type` | 1 | One of: `sedan, hatchback, wagon, coupe, suv, crossover, pickup, van, convertible, other` | `["body_type","hatchback"]` |
| `fuel_type` | 1 | One of: `gasoline, diesel, hybrid, plugin_hybrid, electric, hydrogen, lpg, cng, other` | `["fuel_type","gasoline"]` |
| `transmission` | 1 | One of: `manual, automatic, dual_clutch, cvt, ev_single, other` | `["transmission","manual"]` |
| `mileage_band` | 1 | Bucketed mileage. See bands below. | `["mileage_band","50k-75k"]` |
| `acp` | 1 | ACP endpoint where photos and rich content are streamed agent-to-agent | `["acp","https://a.io/acp"]` |
| `photos_via` | 1 | Indicates how photos are delivered. Default `"acp"`. | `["photos_via","acp"]` |

## Recommended tags

| Tag | Cardinality | Purpose |
|---|---|---|
| `engine_cc` | 0 or 1 | Engine displacement in cc (e.g. `"1998"`) |
| `power_kw` | 0 or 1 | Power output in kW (e.g. `"110"`) |
| `drivetrain` | 0 or 1 | `fwd`, `rwd`, `awd`, `4wd` |
| `color_exterior` | 0 or 1 | Lowercase common name |
| `color_interior` | 0 or 1 | Lowercase common name |
| `vin_last4` | 0 or 1 | Last 4 of VIN (full VIN never publicly tagged) |
| `status` | 0 or 1 | `available, reserved, sold, archived` (default `available`) |
| `expires_at` | 0 or 1 | Unix timestamp; defaults to publish + 30 days |
| `accepts_offer` | 0 or 1 | `yes` / `no` — seller is open to counter-offers |
| `bid_min_cents` | 0 or 1 | If accepts_offer=yes, minimum acceptable bid |
| `delivery` | 0 or 1 | `pickup, ship_buyer, ship_seller, both` |
| `inspection` | 0 or 1 | `welcome, by_appointment, no` |
| `service_history` | 0 or 1 | `full_records, partial, none` |
| `accident_history` | 0 or 1 | `none_known, minor, major` |
| `owners_count` | 0 or 1 | Integer string, e.g. `"1"`, `"2"`, `"3+"` |
| `badge` | 0+ | `verified_seller`, `verified_dealer`, etc. — references NIP-58 events the issuer signed for the seller |

## Optional / advanced

| Tag | Purpose |
|---|---|
| `model_variant` | Trim level, e.g. `"sport"`, `"touring"` |
| `region_geohash` | 5-char geohash for fine-grained region search without leaking exact location |
| `language` | ISO code of the listing language (default `en`) |
| `currency_alt` | Alternative currency the seller accepts (e.g. `"USD"`) |
| `comparable_listings` | One or more `e` tags pointing to comparable NIP-99 events |
| `schema_version` | Cars-pack schema version (current: `"1"`) |

## Mileage bands

Discrete buckets so filters work as tag matches:

```
0-10k, 10k-25k, 25k-50k, 50k-75k, 75k-100k, 100k-150k, 150k-200k, 200k+
```

Always use kilometers. For miles-region listings, convert (1 mi ≈ 1.609
km). Buyers' filters compose by listing acceptable bands as
`["#mileage_band", ["0-10k","10k-25k","25k-50k"]]`.

## Price bands

```
EUR: 0-2k, 2k-5k, 5k-10k, 10k-20k, 20k-35k, 35k-60k, 60k-100k, 100k+
```

Use the seller's listing currency. Cross-currency filtering is the
buyer client's responsibility.

## Region pattern

Hierarchical with `/` separators:

```
EU/CZ/Prague          ← country, city
EU/CZ/Prague/Vinohrady ← optional district
NA/US/CA/SF           ← continent / country / state / city
```

Buyer filters use prefix matching (`EU/CZ/%`).

## What is NEVER on the public listing

These fields stay on the seller's machine and are shared only on
explicit grant during 1-to-1 inquiry, **delivered as ACP content
blocks** (`ImageContentBlock`, `EmbeddedResourceContentBlock`)
direct to the requesting buyer's agent:

- Full VIN (only `vin_last4` ever public)
- Owner name, contact info, address
- All photos — including the cover photo. v1 listings carry no
  `image` tag. Photos arrive in the buyer's agent via ACP after the
  seller's agent grants the inquiry.
- Service-record PDFs
- Title / registration scans
- Insurance / inspection certificates
- Exact GPS location

## Example: minimal valid listing

```json
{
  "kind": 30402,
  "tags": [
    ["d", "8f4a2b1e-6c0d-4f29-9bd3-..."],
    ["title", "2018 Mazda 3 hatchback"],
    ["summary", "65k mi, 1 owner"],
    ["t", "cars"],
    ["t", "mazda"],
    ["t", "mazda3"],
    ["price", "15000", "EUR", ""],
    ["location", "EU/CZ/Prague"],
    ["make", "mazda"],
    ["model", "3"],
    ["year", "2018"],
    ["body_type", "hatchback"],
    ["fuel_type", "gasoline"],
    ["transmission", "manual"],
    ["mileage_band", "50k-75k"],
    ["acp", "https://a.io/acp"],
    ["photos_via", "acp"]
  ],
  "content": "Single owner, full Mazda dealer service history, no accidents."
}
```

See `example_listing.json` for the fully-tagged version.

## Compatibility

- Forward-compatible with broader Nostr marketplace clients (Plebeian
  Market, future tools): they read `title`, `summary`, `price`,
  `location`, `t`. They ignore tags they don't recognize.
- The car-specific tags (`make`, `model`, `mileage_band`, etc.) are
  prefixed with neither `cars-` nor `t=` so they're cheap one-shot
  filter queries on relay indexes.

## Versioning

This schema is **v1**. Future versions add tags only, never rename
or remove. The pack ships with `schema_version: "1"` so clients warn
on unknown major bumps.
