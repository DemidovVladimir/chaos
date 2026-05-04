# Monitoring — Mode A relay

What to watch, where, and what to alert on.

## Metrics to collect

| Metric | Source | Reason |
|---|---|---|
| `strfry_events_inserted_total` | strfry stats | Discovery health — drops to 0 = something broken |
| `strfry_events_rejected_total{reason}` | strfry | Spam patterns; track per `reason` |
| `strfry_active_connections` | strfry | WebSocket health |
| `strfry_query_p99_ms` | strfry | Index performance |
| `strfry_db_size_bytes` | filesystem | Disk planning |
| `caddy_http_requests_total{code}` | Caddy logs | Traffic shape |
| `node_memory_MemAvailable_bytes` | node-exporter | Host health |
| `node_filesystem_avail_bytes{mountpoint="/"}` | node-exporter | Disk free |
| `node_load1` | node-exporter | CPU pressure |

If strfry's release doesn't include native Prometheus output, write
a small adapter (~50 lines Python) that parses `strfry monitor`
output and exposes it on `:9101`.

## Dashboards

One Grafana dashboard with three rows:

1. **Discovery health** — events inserted / rejected per minute, top 5
   rejection reasons, connection count
2. **Performance** — query p50 / p95 / p99 latency, ingestion rate,
   DB size growth
3. **Host** — CPU, RAM, disk, network

## Alerts

Send to whatever channel you'll actually look at — Telegram, email,
Slack. Recommended set:

| Alert | Threshold | Severity |
|---|---|---|
| Relay unreachable from external probe | > 2 min | page (P1) |
| Cert expiry | < 7 days | warn |
| Disk free | < 20% | warn |
| Disk free | < 5% | page |
| Events inserted / 5min | == 0 (and previous day at same hour was > 50) | warn |
| Rejection rate | > 30% over 5 min | warn (likely a bug or attack) |
| `strfry_query_p99_ms` | > 500 ms over 5 min | warn |
| Caddy 5xx rate | > 5% over 5 min | warn |
| Host load1 | > 2× CPU count for 10 min | warn |

## External canary

A tiny script on a separate host that publishes a canary kind-1
event to your relay every 5 minutes and reads it back. If the round-
trip fails, alert. Catches DNS, TLS, network issues that in-host
metrics miss.

```python
# canary.py — run on a separate host every 5 minutes via cron
import time, websockets, asyncio, json, os
from pynostr.event import Event
from pynostr.key import PrivateKey

async def main():
    sk_hex = os.environ["CANARY_SK"]
    relay  = "wss://relay.your-domain.app"

    sk = PrivateKey.from_hex(sk_hex)
    ev = Event(kind=1, content=f"canary {int(time.time())}",
               created_at=int(time.time()), pub_key=sk.public_key.hex())
    ev.sign(sk.hex())

    async with websockets.connect(relay, open_timeout=10) as ws:
        await ws.send(json.dumps(["EVENT", ev.to_dict()]))
        ack = await asyncio.wait_for(ws.recv(), timeout=10)
        if "true" not in ack:
            raise RuntimeError(f"relay rejected: {ack}")
        await ws.send(json.dumps(["REQ", "canary", {"ids": [ev.id], "limit": 1}]))
        await asyncio.wait_for(ws.recv(), timeout=10)

asyncio.run(main())
```

## Log retention

- Caddy access logs — 30 days at `/data/access.log` with rotation
- strfry logs — capture stdout via Docker, 30 days
- Moderation log — append-only forever (small file, few KB / month)
- Backup snapshots — 14 days local, 90 days off-site

## What "healthy" looks like at v1 scale

After ~1 month of soft launch with ~50 active users:

- 1k–5k events inserted / day
- < 5% rejection rate
- p99 query latency < 100 ms
- DB size < 100 MB
- Host load average < 0.5
- 50–200 concurrent WebSocket connections during peak hours

If your numbers are an order of magnitude away from these, investigate.

## When to scale

- Sustained > 500 events/sec → vertical scale (CX32 or bigger)
- > 5k concurrent connections → tune kernel + run 2 strfry replicas
  behind nginx TCP load balancing
- DB size > 10 GB → expand storage
- Cross-region latency complaints → add a second relay in a
  different region, advertise both URLs in the cars-pack default
  list
