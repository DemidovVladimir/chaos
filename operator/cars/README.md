# operator/cars — Mode A Nostr relay deployment for the cars vertical

The deployable part of chaos's cars-vertical registry. One
strfry instance behind Caddy on a small VPS. Cost: ~€5–7/month
all-in. The sibling `operator/cars/admin-agent/` folder runs the
opt-in admin-agent for dispute resolution.

## Files

```
operator/cars/
├── README.md                     this file
├── strfry-compose.yml            Docker Compose for strfry + Caddy + node-exporter (production)
├── strfry-compose.local.yml      local-dev overlay (no TLS, no Caddy, 127.0.0.1:7777)
├── strfry-config.toml            production strfry config (kinds allowlist, PoW=20, rate limits)
├── strfry-config.local.toml      local-dev strfry config (PoW=0, placeholder pubkey)
├── caddyfile                     reverse proxy with auto-LE TLS + NIP-11 (production)
├── writePolicy.js                kind allowlist + per-pubkey rate limits (both modes)
├── verify_relay.py               WebSocket smoke test for a local relay
├── moderation_policy.md          published transparency policy + operator runbook
├── backup.md                     daily snapshot script + restore drill
├── monitoring.md                 metrics, alerts, external canary
└── admin-agent/                  opt-in dispute-resolution Hermes instance
```

## Quick start: 5-min local relay

Want to demo the MVP against your own strfry instead of the public
relays (which 503 under load)? Two paths — pick one.

### Path A — Docker (recommended)

Requires Docker + Docker Compose. The local overlay (`strfry-compose.local.yml`)
disables Caddy + TLS + node-exporter, swaps in `strfry-config.local.toml`
(PoW gate dropped from 20 to 0 so the MVP doesn't have to mine), and
binds strfry's WebSocket to `127.0.0.1:7777` only.

```bash
cd operator/cars

# Boot
docker compose -f strfry-compose.yml -f strfry-compose.local.yml up -d

# Health check (NIP-11 fallback string from strfry over plain HTTP)
curl http://localhost:7777
# expected: "Please use a Nostr client to connect to this server."

# Tear down
docker compose -f strfry-compose.yml -f strfry-compose.local.yml down
```

The production path is unchanged: a deployment without `-f strfry-compose.local.yml`
still uses Caddy + TLS + the production config + PoW=20.

### Path B — `brew install strfry` (macOS, no Docker)

If `strfry` isn't in your Homebrew taps, build from source per the
upstream instructions at https://github.com/hoytech/strfry (≈10 min on
an M1 / M2). Then:

```bash
cd operator/cars

# Run strfry directly against the local config. strfry writes its LMDB
# files into the configured `db` path; for `strfry-config.local.toml`
# that's /app/strfry-db (the Docker path). For a non-Docker run, edit
# the config's `db = ` line to a writable host path, e.g. ./strfry-db/,
# then:
mkdir -p ./strfry-db
strfry --config strfry-config.local.toml relay
```

strfry will log `Started websocket server on 0.0.0.0:7777`. Leave it
running; in another terminal, run `verify_relay.py` (below). Stop with
`Ctrl-C`.

### Verifying your relay works

After either Path A or Path B, run the included smoke test from a
second terminal:

```bash
cd operator/cars
python3 verify_relay.py
```

Expected output (a healthy relay sends `EOSE` once it has streamed all
matching events — for a freshly booted relay, that's instantly):

```
[+] connected to ws://localhost:7777, awaiting frames...
["EOSE","verify"]
[+] relay is healthy (got EOSE)
```

If you see `failed to reach ws://localhost:7777`, the relay isn't
running. Check `docker compose ps` (Path A) or that strfry's terminal
hasn't exited (Path B).

For an end-to-end check (publish a NIP-99 listing + receive it), point
the MVP at the local relay — see `mvp/README.md` § "Optional: point at
your own Mode-A relay".

## 30-minute deployment

1. Provision the VPS (Hetzner CX22, DigitalOcean s-2vcpu-4gb, or
   Modal). Open inbound TCP 80 and 443.
2. Point `relay.<your-domain>` A record at it.
3. Install Docker + Docker Compose.
4. `git clone <this-repo> && cd operator/cars`.
5. Edit `strfry-config.toml`:
   - set `info.name`, `info.description`, `info.contact`
   - set `info.pubkey` to your operator pubkey
   - confirm `events.minPowDifficulty = 20`
6. Edit `caddyfile` — replace `relay.example.app` with your domain.
7. `docker compose up -d`
8. Verify: `curl https://relay.<your-domain>/` should return strfry's
   NIP-11 relay information document.
9. Test publish/subscribe round-trip with a third-party Nostr client
   (Damus, nostr-cli, or `mvp/buyer.py`).

## Cost

Hetzner CX22 (2 vCPU, 4 GB RAM, 40 GB SSD): €4.51/mo. Backups: €1/mo.
Domain: ~€15/year. Caddy + Let's Encrypt: free. **Total ≈ €5–7/month
at v1 scale.**

Will need an upgrade when you hit:

- Sustained > 500 events/sec → CX32 or scale up
- Event DB > 10 GB → expand storage
- > 5,000 concurrent WebSocket connections → tune kernel + consider
  2+ strfry replicas behind a TCP load balancer

## Before going live

- [ ] DNS resolves `relay.<your-domain>` to the VPS
- [ ] Caddy issued a valid Let's Encrypt cert
- [ ] strfry NIP-11 doc returns 200 with your `info.pubkey`
- [ ] Test publish + subscribe round-trips
- [ ] PoW enforcement verified (publish without PoW → rejected)
- [ ] Rate limiter verified (12 events in a minute → 11th rate-limited)
- [ ] Backup cron is running (`backup.md`)
- [ ] Prometheus exporter scrapes successfully (`monitoring.md`)
- [ ] Moderation contact email (`info.contact`) is monitored daily
- [ ] Published moderation policy live at
      `https://moderation.<your-domain>` (`moderation_policy.md`)

## What this relay accepts

Only marketplace + DM kinds. See `strfry-config.toml` for the
allowlist. General Nostr social events (kind 1 text notes, kind 6
reposts) are rejected — direct users to general-purpose relays for
chitchat.

## Ban / unban a pubkey

When a takedown notice arrives or you detect abuse:

```bash
# 1. Drop their events from the local DB
docker exec strfry strfry --config /etc/strfry.conf \
    delete --filter '{"authors":["<bad-pubkey-hex>"]}'

# 2. Add to blocklist
echo "<bad-pubkey-hex>" >> /var/lib/strfry/pubkey_blocklist.txt

# 3. Reload strfry (writePolicy.js re-reads the file)
docker compose restart strfry

# 4. Log the action
echo "{\"at\":\"$(date -u +%FT%TZ)\",\"action\":\"blocklist\",\"pubkey\":\"<bad>\",\"reason\":\"...\"}" \
  >> /var/lib/moderation/log.jsonl
```

This is per-relay. Other relays in the federation are unaffected
unless you publish a NIP-51 mute list under your operator pubkey
naming the bad actors.

## Federation note

You don't have to be the only relay. The default cars-pack relay list
in the seller / buyer config ships with `wss://relay.<your-domain>`
plus 2–3 community ones. Buyers' agents subscribe to all; sellers
publish to all. Your relay gives you moderation control over your
slice of the network; it cannot reach into community relays.

## See also

- `../../PROTOCOL.md` for the on-the-wire design
- `../../SECURITY.md` for the threat model and pre-launch checklist
- `../../reputation/dispute_protocol.md` for the admin-agent dispute flow
- `moderation_policy.md` for the published policy + operator runbook
- `backup.md` and `monitoring.md` for ops
- `admin-agent/README.md` for the opt-in dispute-resolution agent
