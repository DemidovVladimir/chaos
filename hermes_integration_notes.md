# Hermes Integration Notes

Reverse-engineered from `hermes-agent` source @ commit-time of writing.
This is the contract chaos plugins must conform to. Update when
Hermes' plugin API changes.

## TL;DR

Hermes ships a real plugin system (`hermes_cli/plugins.py`). It looks
for `plugin.yaml` + `__init__.py` with a `register(ctx)` function in:

1. `<repo>/plugins/<name>/` (bundled)
2. `~/.hermes/plugins/<name>/` (user)
3. `./.hermes/plugins/<name>/` (project, gated by `HERMES_ENABLE_PROJECT_PLUGINS`)
4. Pip packages exposing entry-point group `hermes_agent.plugins`

The chaos plugin scaffolds (`plugins/cars`,
`plugins/cars`) currently call APIs that **do not exist** on
Hermes' `PluginContext`:

- `ctx.resolve_dependency(...)` — does not exist
- `ctx.register_pack_contract(...)` — does not exist
- `ctx.install_capability_mcp(...)` — does not exist
- `ctx.config` — does not exist
- `ctx.register_skill(path=...)` — wrong signature; real signature is
  `register_skill(name: str, path: Path, description: str = "")`

So today the plugins would `ImportError`/`AttributeError` immediately
on register.

## Phase 1 findings — quick bullets

1. **Plugin discovery**: `PluginManager.discover_and_load()`
   (`hermes-agent/hermes_cli/plugins.py:614`). Scans the four sources
   above, parses `plugin.yaml` into a `PluginManifest`, then imports
   each plugin's `__init__.py` as `hermes_plugins.<slug>` and calls
   `register(ctx)`.

2. **`plugin.yaml` keys Hermes actually reads**
   (`plugins.py:889–901`): `name`, `version`, `description`, `author`,
   `requires_env`, `provides_tools`, `provides_hooks`, `kind`
   (one of `standalone | backend | exclusive | platform`). Anything
   else (e.g. our `entry_point`, `dependencies`, `includes`,
   `forbidden_toolsets`, `config`) is **silently ignored** —
   documentation-only.

3. **Opt-in by default**: a plugin only loads if its `key` (path-derived,
   e.g. `cars`) is in `plugins.enabled` in `~/.hermes/config.yaml`,
   unless it's bundled with `kind: backend` or `kind: platform`
   (`plugins.py:717`). Our cars plugins must be `kind: standalone`
   and the user has to enable them explicitly.

4. **`ctx` is a `PluginContext`** (`plugins.py:230`). Methods
   available:
   - `register_tool(name, toolset, schema, handler, check_fn=None,
     requires_env=None, is_async=False, description="", emoji="")`
     (`plugins.py:239`)
   - `register_hook(hook_name, callback)` (`plugins.py:525`)
   - `register_skill(name, path, description="")` — **`path` must be a
     `pathlib.Path` and the file must exist or it raises**
     (`plugins.py:544`). Skills become resolvable as
     `<plugin_name>:<name>`; not auto-listed in the system prompt.
   - `register_cli_command(name, help, setup_fn, handler_fn=None,
     description="")` (`plugins.py:298`)
   - `register_command(name, handler, description="", args_hint="")`
     — slash command (`plugins.py:323`)
   - `register_platform(...)` (`plugins.py:469`)
   - `register_image_gen_provider(provider)` (`plugins.py:442`)
   - `register_context_engine(engine)` (`plugins.py:410`)
   - `dispatch_tool(tool_name, args, **kwargs)` (`plugins.py:379`)
   - `inject_message(content, role="user")` (`plugins.py:270`)

   There is **no** `register_mcp_server`, no `resolve_dependency`,
   no `register_pack_contract`, no `install_capability_mcp`, no
   `ctx.config`. If we want those abstractions they have to be
   chaos's own helpers, not Hermes API.

5. **Skill loading**: skills live as `<dir>/SKILL.md` files (markdown
   with YAML front-matter) and Hermes resolves them via
   `agent/skill_utils.py:1`. `register_skill` just records a
   `(name, path)` pair so the skill can be loaded explicitly via
   `skill_view()` or as a subagent prompt; it does **not** parse
   `requires_tools` or `exposes_mcp_tools` automatically.

6. **MCP servers — both directions**:
   - **Hermes-as-MCP-server**: `mcp_serve.py` is a one-shot CLI
     (`hermes mcp serve`) that exposes Hermes' chat history as MCP
     tools over **stdio**. It is not a per-plugin facility.
     A plugin that wants to host its own FastMCP server has to do it
     itself (start a thread / process at `register()` time, or
     register a `register_cli_command` like `hermes chaos-agent
     serve`).
   - **Hermes-as-MCP-client**: `tools/mcp_tool.py:2795`
     `register_mcp_servers(servers: Dict[str, dict])` registers
     remote MCP servers from a dict (key = server name, value =
     `{command, args, env, enabled}`). Each remote tool becomes a
     namespaced Hermes tool. This is the path for any seeking-side agent
     plugin to dial publishers — but typical use is
     project-local (`./.hermes/mcp.json`-style), not per-call.

7. **Toolset isolation enforcement (Rule 11)**: aspirational for now.
   No CI lint exists in Hermes that inspects chaos's
   `forbidden_toolsets` field — it's just YAML. Enforcement would
   need to be a separate `tools/lint_plugins.py` script we ship.

8. **Identity / keys**: Hermes does not custody any keys. Hermes' own
   secrets land in `~/.hermes/.env` and `~/.hermes/auth.json`
   (`hermes_constants.get_hermes_home()`). chaos keeps its
   keys at `~/.chaos/keys/agent.key` (mode 0600 per AGENTS.md
   Rule 3) — Hermes does not need to know about them.

9. **Logging**: `logging.getLogger(__name__)` is fine; Hermes
   configures the root logger. `logger.info/warning/error` shows up
   in normal Hermes output.

10. **Errors during register**: caught and logged at
    `plugins.py:986`; loaded plugin gets `enabled=False, error=str`.
    A `register()` that raises does **not** crash Hermes — but the
    plugin won't load either.

## Phase 2 — Recommended minimal scope: TIGHTEST + skill registration

Why not "ambitious" (MVP logic moved into the plugin):
- Hermes provides no `register_mcp_server`. Spinning up FastMCP
  inside `register()` would block plugin discovery.
- The offering agent engine (`agent/src/chaos_agent/`) is currently
  also stub-and-`NotImplementedError`. The working logic lives in
  `mvp/agent_offering.py`, which is a script not a library. Rewriting it
  cleanly into a plugin is a multi-day job — out of scope here.

Why not "tightest" (NoOp register):
- The current scaffolds raise `NotImplementedError` at import time —
  failing in a way that *is* technically the documented "errors
  disable the plugin" path, but produces a confusing log line and
  doesn't even exercise the manifest. We can do better with a few
  hours of work.

**Chosen — "modest"**: Make `register(ctx)` actually run to
completion. It:

1. Registers a CLI subcommand (`hermes cars …`) that delegates
   to the existing `mvp/agent_offering.py` script via `subprocess` for now.
   This lets users actually use the plugin to run the working MVP
   without touching offering agent engine internals.
2. Registers the offering-cars / seeking-cars `SKILL.md` from
   `verticals/cars-pack/skills/<role>-cars/SKILL.md` so the agent
   has access to the role description as a skill (`cars:main`).
3. Registers a slash command (`/cars status`,
   `/cars watch`) so plugin presence is visible in-session.
4. Logs which steps it took.

This produces a verifiably-loadable plugin against Hermes (Hermes
prints `Plugin discovery complete: 2 found, 2 enabled`), gives users
a real slash command + CLI subcommand, and unblocks Phase 4 testing
without rewriting the engine.

## Phase 3 — files we'll edit

- `plugins/cars/plugin.yaml` — drop nonexistent keys, add
  `kind: standalone`, keep `requires_env` / `description` / `version`.
- `plugins/cars/pyproject.toml` — fix `package-data` glob,
  drop entry-point group (Hermes finds us via dir scan, not pip).
- `plugins/cars/src/chaos_cars_seller/__init__.py` —
  real `register(ctx)` calling Hermes APIs.
- `plugins/cars/src/chaos_cars_seller/register.py` —
  delete or replace; the registration lives in `__init__.py`.
- Same for `plugins/cars/`.

We do NOT touch `agent/`, `agent/`, `mvp/`, or `verticals/` per
constraints.

## Future work (not in scope here)

- Implement the offering agent / seeking agent engines so the plugin can drive them
  in-process instead of `subprocess`-shelling out to `mvp/agent_offering.py`.
- Build a `lint_plugin.py` in `plugins/_template/` that enforces
  AGENTS.md Rule 11 against the manifest's `forbidden_toolsets`.
- Add a `register_mcp_server` method to a chaos `PluginContext`
  wrapper, so the offering-side plugin can spawn its FastMCP at register time.
- Once agent engines exist, drop the `subprocess` shim.
