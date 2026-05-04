# plugins/ — role-vertical install plugins

End users install plugins from this folder. Each plugin is a thin
**Hermes-plugin wrapper** that combines:

- a **universal engine** (`seller/`, `buyer/`, or
  `admin-engine/`) as a dependency,
- a **vertical pack contract** (e.g. `cars-pack@1`) plus its skill
  for this role,
- zero or more **capability MCPs** (from `shared-mcp/` and/or the
  vertical pack's own `mcp/` folder).

The user installs **one plugin per (role × vertical) pair** they
participate in. A user who buys cars and sells watches installs
`cars-buyer` + `watches-seller`. A user who only buys cars installs
just `cars-buyer`. Multi-vertical buyers install one plugin per
vertical they're shopping in.

## Naming

`<vertical>-<role>` for end-user plugins. `<vertical>-admin` for
operator-deployed admin variants. `chaos-<feature>` for cross-
vertical plugins.

## Cars-pack plugin family

| Plugin | Audience | Approx size | Notes |
|---|---|---:|---|
| `cars-seller` | Anyone selling cars | ~50 KB | Universal seller engine + cars skill + cars contract. No local capability MCPs. |
| `cars-buyer` | Anyone buying cars (free tier) | ~150 KB | Universal buyer engine + cars skill + `reverse-image-mcp` (fast mode), `market-comp-mcp` (fast), `vin-decoder-mcp` (cars-pack), `reputation-mcp` (fast). |
| `cars-admin` | Vertical operators only | ~60 KB | Admin engine + admin-cars skill. NOT for end users. |
| `chaos-pro` | Cross-vertical paid upgrade | ~10 KB | Flips capability MCPs into thorough/pro tier mode for ALL installed buyer plugins. ONE subscription, applies to every vertical. |

## The cross-vertical pro model

`chaos-pro` is **not per-vertical**. We do NOT ship
`cars-buyer-pro`, `watches-buyer-pro`, etc. Instead:

- Free buyer plugin (`cars-buyer`) ships its capability MCPs in
  **fast tier** mode via a config flag (`pro_mode: false`).
- `chaos-pro` is a single mega-plugin the user installs once.
  It flips `reverse-image-mcp` + `market-comp-mcp` +
  `reputation-mcp` into **thorough tier** for every installed buyer
  plugin, regardless of vertical.
- One subscription, all verticals. Lower friction than per-vertical
  pro variants and aligned with `BUSINESS_MODEL.md`.

## `_template/`

Copy-and-fill skeleton for adding a new role-vertical plugin. See
`_template/README.md` for the checklist.

## Adding a new vertical

For a new vertical `foo`:

1. Author the pack at `verticals/foo-pack/` (tag schema, skills, any
   pack-specific MCPs).
2. Copy `plugins/_template/` to `plugins/foo-seller/` and
   `plugins/foo-buyer/`. Fill in the manifests.
3. Add foo-buyer to `chaos-pro`'s `extends` list so the cross-
   vertical pro upgrade applies automatically.
4. Author `plugins/foo-admin/` only if a dedicated vertical operator
   role makes sense.
