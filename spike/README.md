<!-- (Historical -- written under the project's previous name "neuro-spati", now called "chaos".) -->

# spike — peer-transport binary round-trip

> **MCP is the chosen wire.** See [`MCP_SPIKE_REPORT.md`](MCP_SPIKE_REPORT.md)
> for the verdict and `seller_mcp.py` / `buyer_mcp.py` for the live
> reference implementation. The ACP and A2A spikes (`seller_acp.py`,
> `buyer_acp.py`, `buyer_a2a.py`, `seller_a2a.py`,
> [`A2A_SPIKE_REPORT.md`](A2A_SPIKE_REPORT.md)) are kept here for
> historical context but are **superseded** — do not use them as a
> basis for the production seller/ or buyer/ components.

---

## Historical: ACP `ImageContentBlock` round-trip

A two-process Python experiment that answers one question: **can ACP move binary content between two agents end-to-end via the published `ImageContentBlock` / `EmbeddedResourceContentBlock` types?**

**Answer: yes.** Verified against `agent-client-protocol` 0.9.0 on 2026-05-02. (Superseded by the MCP spike — kept below for traceability.)

## What was tested

Two separate Python processes:

- **`seller_acp.py`** — implements `acp.Agent`, run via `acp.run_agent(...)` over stdio.
- **`buyer_acp.py`** — implements `acp.Client`, spawns the seller as a subprocess via `acp.spawn_agent_process(...)`, sends a `prompt`, captures the stream of `session_update` callbacks, and verifies the bytes by SHA-256.

The seller emits a four-block stream on every prompt:

1. `TextContentBlock` — opening line ("sending photo + inspection report...")
2. `ImageContentBlock` — real 69-byte PNG (1×1 red pixel), base64 inline
3. `EmbeddedResourceContentBlock` — 238-byte "inspection report" (text/plain, base64 blob)
4. `TextContentBlock` — closing line

The buyer decodes each block, hashes the bytes, compares to expected.

## Run it yourself

```bash
cd spike
python3 buyer_acp.py
# → ... [buyer] PASS image sha256 matches (69 bytes)
# → ... [buyer] PASS resource sha256 matches (238 bytes)
# → === SPIKE PASS ===
```

Decoded artifacts land in `received/` so you can verify visually:

- `received/received_image.png` — opens as a 1×1 red pixel
- `received/received_report.txt` — the inspection-report text

## Result log (last successful run)

```
[buyer]  Spawning seller: .../spike/seller_acp.py
[buyer]  Connected to seller.
[buyer]  initialized; agent=neuro-spati-spike-seller
[buyer]  session=spike-1777743161099
[buyer]  → prompt
[buyer]    text len=56
[buyer]    image bytes=69 mime=image/png sha256=c19c64e14541…
[buyer]    resource uri=local://inspection-report.txt mime=text/plain bytes=238 sha256=c75542c6c985…
[buyer]    text len=70
[buyer]  ← prompt stop=end_turn
[buyer]  PASS image sha256 matches (69 bytes)
[buyer]  PASS resource sha256 matches (238 bytes)
=== SPIKE PASS ===
```

## What this unlocks

The v5 architecture decision **"photos move agent-to-agent over ACP, never via HTTP file servers"** is unblocked at the API level. The `seller-cars/SKILL.md` § "Inquiry-handling policy" can call `acp.image_block(...)` and `acp.resource_block(acp.embedded_blob_resource(...))` exactly as written.

The implementation plans in `seller/IMPLEMENTATION_PLAN.md` and `buyer/IMPLEMENTATION_PLAN.md` flagged this as the #1 open question; consider it answered.

## API gotcha worth noting

The two helpers compose differently:

```python
# image — image_block returns a complete ImageContentBlock; no extra wrap
acp.update_agent_message(
    acp.image_block(data=b64, mime_type="image/png")
)

# resource — embedded_blob_resource returns BlobResourceContents (the
# INNER data); you must wrap it with acp.resource_block(...) to get an
# EmbeddedResourceContentBlock that update_agent_message can carry.
acp.update_agent_message(
    acp.resource_block(
        acp.embedded_blob_resource(
            uri="...",
            blob=b64,
            mime_type="...",
        )
    )
)
```

The first version of this spike used `update_agent_message(embedded_blob_resource(...))` directly, which silently hung the message pipe. Likely cause: the server tried to serialize a `BlobResourceContents` as a `ContentBlock`, the discriminated-union dispatch rejected it, and the underlying JSON-RPC stream dropped without surfacing the error. **Lesson for the implementation: every content-block emit goes through `acp.X_block(...)` first; never pass raw inner-data types into `update_agent_message`.**

This is the kind of thing that won't show up in the type checker (the helpers are unannotated as `BlobResourceContents` vs `ContentBlock` and Python won't catch it) but will make the agent silently unreachable in production. Worth a unit test in `seller/tests/test_acp_session.py`: assert that every emit passes through the right wrapping helper.

## What this spike did NOT prove

The architecture has three remaining unknowns. The spike didn't address them; it only resolved the API question.

| Open question | Status | Where to address |
|---|---|---|
| Cross-network transport (HTTP+SSE / WebSocket vs. stdio) | `acp` 0.9.0 ships **stdio only**. We need an HTTP+SSE bridge ourselves. | Follow-up spike: wrap `AgentSideConnection` over `aiohttp.web` + SSE. ~150 lines. |
| Large-payload performance (10 MB+ photos) | Tested 69-byte PNG + 238-byte text. JSON-RPC + base64 of multi-MB blobs may hit memory/latency limits. | Follow-up spike: emit 10 chunks of 1 MB each, measure RTT and memory. |
| Hermes plugin integration | Used standalone `acp.Agent`. The seller plugin's runtime composition (Hermes lifecycle vs. `MarketplaceSellerACPAgent`) is still open. | Resolve in week 1 of `LAUNCH_PLAN.md` per `seller/IMPLEMENTATION_PLAN.md` Day 3. |

The first one is the most important. **Without HTTP+SSE, the v5 cross-network claim isn't deliverable.** The library doesn't ship it, so we either build a small bridge or pick an alternate transport. Either is a 1–2 day spike, not a week.

## Files

- `seller_acp.py` — 142 lines, `acp.Agent` subclass with the four-block emit
- `buyer_acp.py` — 175 lines, `acp.Client` subclass that spawns the seller, drives one prompt, verifies SHA-256
- `received/` — output directory; populated on successful run
- `README.md` — this file

No external test fixtures needed. The PNG is a 67-byte hex literal embedded in both files; the report is a hardcoded byte string. Both are SHA-256 compared at the end.

## Lifecycle notes

- The buyer is the parent process; it spawns the seller via `acp.spawn_agent_process(...)`. The seller terminates when its parent's stdout/stdin closes.
- The buyer has a 15-second hard timeout (`asyncio.wait_for`) wrapping the whole session, so a stuck seller (or a hung resource block emit, as in the first iteration of this spike) won't block forever.
- The `proc.terminate()` call before context-manager exit shuts the seller down cleanly. Without it, the spike would hang for ~10s waiting for the subprocess to flush stdin EOF.

## Reproducibility

The spike requires `agent-client-protocol>=0.9.0,<1.0` and Python 3.10+. Install:

```bash
pip install agent-client-protocol
python3 buyer_acp.py
```

No other dependencies. Self-contained.
