# plugins/_template — role-vertical plugin scaffold

Copy this folder to `plugins/<vertical>-<role>/` and fill in the
placeholders. Every role-vertical plugin must:

1. Declare the **universal engine** (`chaos-agent`,
   `chaos-agent`, or `chaos-admin-engine`) as a
   dependency.
2. Include the **skill** for (role × vertical) from the pack at
   `verticals/<vertical>-pack/skills/<role>-<vertical>/SKILL.md`.
3. Bind the **pack contract** (`<vertical>-pack@<version>`).
4. List the **capability MCPs** the role needs. Universal MCPs come
   from `shared-mcp/`; vertical-specific ones from
   `verticals/<vertical>-pack/mcp/`.
5. Include `forbidden_toolsets` to constrain the agent.
6. Document required env vars.

## Files in this template

- `plugin.yaml` — Hermes plugin manifest. The placeholders are
  `<PLACEHOLDER_…>` markers; replace each.
- `pyproject.toml` — Python package skeleton. Entry point pattern
  is `chaos_<vertical>_<role>:register`.
- `src/chaos_<vertical>_<role>/register.py` — `register(ctx)`
  function that wires the engine + skill + pack contract +
  capability MCPs at install time.
- `README.md` — what the plugin does, who installs it.

## Checklist before opening a PR

- [ ] All YAML placeholders replaced.
- [ ] Skill path actually exists in the pack (or the parallel agent
      that's writing the skill has shipped it).
- [ ] Capability MCPs listed all exist as folders (under
      `shared-mcp/` or `verticals/<vertical>-pack/mcp/`).
- [ ] `forbidden_toolsets` includes everything the role doesn't
      need.
- [ ] No new HTTP host introduced for binary content (AGENTS.md
      rule 2).
