# registry — Mode A Nostr relay deployment

The deployable part of neuro-spati's registry. One strfry instance
behind Caddy on a small VPS. Cost: ~€5–7/month all-in.

## Files

```
registry/
├── README.md                     this file
├── strfry-compose.yml            Docker Compose for strfry + Caddy + node-exporter
├── strfry-config.toml            strfry configuration (kinds allowlist, PoW, rate limits)
├── caddyfile                     reverse proxy with auto-LE TLS + NIP-11
├── moderation_policy.md          published transparency policy + operator runbook
├── backup.md                     daily snapshot script + restore drill
└── monitoring.md                 metrics, alerts, external canary
```

## 30-minute deployment

1. Provision the VPS (Hetzner CX22, DigitalOcean s-2vcpu-4gb, or
   Modal). Open inbound TCP 80 and 443.
2. Point `relay.<your-domain>` A record at it.
3. Install Docker + Docker Compose.
4. `git clone <this-repo> && cd registry`.
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

- `../PROTOCOL.md` for the on-the-wire design
- `../SECURITY.md` for the threat model and pre-launch checklist
- `moderation_policy.md` for the published policy + operator runbook
- `backup.md` and `monitoring.md` for ops
