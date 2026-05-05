# sample_photos/

Placeholder photo fixtures for the MVP. These are minimal valid PNGs
generated at first run by `mcp_server.py` if missing — intentionally
tiny (1×1 pixel) so the demo has zero file-size friction.

In production you'd drop your real cover, exterior, interior,
engine_bay, undercarriage, and odometer photos here, and
`request_photos` would return them as `ImageContent` blocks per the
cars-pack@1 contract.

**Multi-listing layout**: when running `agent_offering.py serve-multi
listings/`, drop per-item assets under `sample_photos/<item_id>/`
(any number of `*.png` files — all are returned). For inspection
reports, drop a `.pdf` next to the listing TOML as
`mvp/sample_inspection_<item_id>.pdf` and the MCP server will
auto-detect the MIME type and return it as `application/pdf`
(also accepts `.txt` / `.md`; anything else is served as
`application/octet-stream`). Missing per-item assets fall back to
the global `cover.png` + `sample_inspection.txt` fixtures.

**Privacy note**: photos containing license plates, VIN stickers,
or interior documents must NEVER be in this folder if you run the
MVP against a real network. The MVP assumes localhost-only and
fixture data. Production cars plugins (`plugins/cars`)
gate license-plate / interior-with-documents photo kinds via
explicit user-confirm grants — see
`verticals/cars-pack/skills/offering-cars/SKILL.md`.
