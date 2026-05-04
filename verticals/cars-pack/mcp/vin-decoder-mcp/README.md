# `vin-decoder-mcp` — free, local, structural

A pure local MCP that decodes a VIN's structural facts (manufacturer,
plant, year, body shape) using only the VIN string itself. **No
third-party data sources. No vehicle history. No data custody.**
Free.

## What it does

Given a VIN string, return:

- **WMI decode** (positions 1–3): manufacturer, country, manufacturer
  type — from the SAE J272-published WMI registry (public,
  redistributable)
- **VDS decode** (positions 4–9): vehicle attributes encoded by the
  manufacturer
- **Year decode** (position 10): model year — deterministic mapping
- **Plant decode** (position 11): assembly plant code
- **Check-digit validation** (position 9 for North American VINs):
  mod-11 check that catches typos
- **Cross-check against listing tags**: if the listing claims `make
  =mazda year=2018`, does the VIN agree?

What it does NOT do:

- Look up vehicle history (accidents, owners, title status)
- Look up recall information
- Query any third-party service
- Store the VIN anywhere

## Why this exists as a separate (free) MCP

The data needed to decode VIN structure is **public and
redistributable** (SAE WMI registry, deterministic year codes,
mod-11 check). The data needed for **vehicle history** is commercial
and gatekept. We deliberately do not touch it.

## MCP tool surface

```json
{
  "name": "vin_decode",
  "description": "Decode a VIN's structural facts using only public reference data. Cross-checks against listing claims if provided. Does not look up vehicle history.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "vin": {"type": "string", "minLength": 17, "maxLength": 17,
              "description": "17-character VIN. Letters I, O, Q are not used and will be rejected."},
      "claimed_facts": {
        "type": "object",
        "properties": {
          "make":  {"type": "string"},
          "model": {"type": "string"},
          "year":  {"type": "integer"}
        }
      }
    },
    "required": ["vin"]
  }
}
```

Returns:

```json
{
  "vin": "JM1BL1H51A1234567",
  "decoded": {
    "wmi": "JM1",
    "manufacturer": "mazda",
    "country": "japan",
    "manufacturer_type": "passenger_vehicles_high_volume",
    "vds": "BL1H51",
    "year": 2010,
    "plant": "hofu",
    "check_digit_valid": true
  },
  "contradictions": [
    "claimed year=2018 but VIN year position decodes to 2010"
  ],
  "warnings": [],
  "data_sources_used": ["sae_wmi_registry_2024", "iso_3779_year_codes"]
}
```

## Pricing

**Free.** No API key, no auth, no rate limit beyond reasonable abuse
protection (1k requests per IP per hour).

## Implementation outline

```
vin-decoder-mcp/
├── pyproject.toml
├── server.py
├── data/
│   ├── wmi_registry.json     ~10k entries; ~500 KB
│   ├── year_codes.json       30-year cycle table
│   └── plant_codes/          per-manufacturer JSON files
├── decode.py                 pure-Python VIN parser
└── tests/
    ├── test_known_vins.py
    └── test_check_digit.py
```

Total code is ~300 lines including tests.

## Use in the cars pack

The buyer-cars skill calls `vin_decode` whenever the seller has
provided a VIN (typically only after the buyer asked for it via
NIP-17 DM and the seller granted). The skill cross-checks the
decoded facts against the listing tags. Contradictions are reported
to the user as red flags.

## What this opens up later

**`vin-attestation-mcp`** (paid, future) — a successor that lets a
**seller** sign a structured attestation about their VIN ("I attest
this VIN, this odometer reading, no salvage title, attached PDF of
inspection report"). The attestation is a signed Nostr event the
seller publishes alongside their listing. The MCP doesn't store
anything; it just helps the seller construct the signed event and
helps the buyer verify the signature + linked PDF.
