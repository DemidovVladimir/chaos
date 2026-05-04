# Multi-listing seller catalog

Drop one `.toml` per car in this directory and run:

```bash
python seller.py serve-multi listings/
```

Each `.toml` is published as its own NIP-99 event. The same MCP
server on `127.0.0.1:8765` serves all of them — resolution by
`item_id` happens at call time inside `mcp_server.py`'s `CATALOG`.

## TOML schema

Use `mvp/sample_car.toml` as a template. Required fields:

- `item_id` — stable per-car id (UUID is fine; this is the catalog
  key)
- `title`, `summary`, `price_amount`, `price_currency`, `location`
- `make`, `model`, `year`, `body_type`, `fuel_type`,
  `transmission`, `mileage_band` (cars-pack@1 facets)
- `mcp_url` — should match wherever the seller's MCP server binds
  (e.g. `http://127.0.0.1:8765/sse`). All listings in a single
  `serve-multi` invocation share one URL.
- `pack` — pack name + version, e.g. `cars-pack@1`
- `content` — free-text body (markdown, text only — photos move
  via MCP)

## Per-item assets

Photos and inspection reports are resolved by `item_id`:

- `mvp/sample_photos/<item_id>/*.png` — listing-specific photos.
  All matching PNGs are returned by `request_photos`.
- `mvp/sample_inspection_<item_id>.{pdf,txt,md}` — listing-specific
  inspection report. MIME type is auto-detected (PDF, plain text,
  markdown, or `application/octet-stream` for anything else).

If either is missing, the server falls back to the global
`mvp/sample_photos/cover.png` + `mvp/sample_inspection.txt` so a
half-populated catalog still demos cleanly.

## Single-listing path

`python seller.py serve sample_car.toml` is unchanged. It bypasses
the catalog entirely; every call returns the global fallback
fixtures. Use it for the simplest one-car demo.
