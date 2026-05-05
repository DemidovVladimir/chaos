"""verify_relay.py — sanity-check a local Mode A strfry relay.

Run after `docker compose -f strfry-compose.yml -f strfry-compose.local.yml
up -d` (or after starting strfry via `brew install strfry`):

    python3 verify_relay.py

Opens a WebSocket to ws://localhost:7777, sends a NIP-01 REQ for any
kind-1 event, prints whatever the relay sends back, then closes. A working
relay returns at least an `EOSE` (end-of-stored-events) frame within a
couple of seconds; if the connection refuses or times out, the relay is
not running on :7777.

Dependencies: `websockets` (already pulled in by mvp/requirements.txt).
If you don't have the MVP venv active:

    pip install websockets

This script is read-only — it never writes events, so it can't pollute
the relay or fall foul of the writePolicy.
"""

from __future__ import annotations

import asyncio
import json
import sys

import websockets

RELAY_URL = "ws://localhost:7777"


async def main() -> int:
    try:
        async with websockets.connect(RELAY_URL, open_timeout=5) as ws:
            await ws.send(json.dumps(["REQ", "verify", {"kinds": [1], "limit": 1}]))
            print(f"[+] connected to {RELAY_URL}, awaiting frames...")
            for _ in range(3):
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=2)
                except TimeoutError:
                    print("[-] no frame within 2s (relay may be idle)")
                    break
                print(msg)
                # Stop on EOSE — confirms the relay parsed our REQ.
                try:
                    parsed = json.loads(msg)
                    if isinstance(parsed, list) and parsed and parsed[0] == "EOSE":
                        print("[+] relay is healthy (got EOSE)")
                        return 0
                except json.JSONDecodeError:
                    pass
            return 0
    except (OSError, websockets.exceptions.WebSocketException) as exc:
        print(f"[-] failed to reach {RELAY_URL}: {exc}")
        print("    is strfry running? try:")
        print("    docker compose -f strfry-compose.yml -f strfry-compose.local.yml up -d")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
