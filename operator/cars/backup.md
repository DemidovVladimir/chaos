# Backup — Mode A relay

The relay's event database is the only state worth backing up.
Photos and inquiries live on offering agent / seeking agent machines; the relay is
the discovery index.

## What to back up

- `strfry-data` Docker volume (LMDB event database)
- `pubkey_allowlist.txt`, `pubkey_blocklist.txt` (operator-managed
  files in the strfry-data volume)
- `/var/lib/moderation/log.jsonl` (audit log)
- `caddy-data` volume (Let's Encrypt certs — easy to regenerate but
  saves rate-limit headaches if you redeploy)
- `caddyfile`, `strfry-config.toml`, `strfry-compose.yml`,
  `writePolicy.js` (your config — these live in git, but back up the
  deployed copies too)

## What NOT to back up

- The relay's "knowledge of users" — there's no user table. Pubkeys
  are sovereign. If the relay loses everything, users republish.
- Photos / DMs — not on the relay.

## Daily snapshot script

`/usr/local/bin/strfry-backup.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

DATE=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP_DIR=/var/backups/relay
LOCAL_PATH="${BACKUP_DIR}/strfry-${DATE}.tar.zst"

mkdir -p "${BACKUP_DIR}"

# strfry's LMDB needs a consistent snapshot. Stop strfry, copy, start.
docker compose -f /opt/relay/strfry-compose.yml stop strfry

tar -I 'zstd -19 -T0' -cf "${LOCAL_PATH}" \
    -C / \
    var/lib/docker/volumes/relay_strfry-data/_data \
    var/lib/moderation/log.jsonl \
    opt/relay/strfry-config.toml \
    opt/relay/strfry-compose.yml \
    opt/relay/caddyfile \
    opt/relay/writePolicy.js

docker compose -f /opt/relay/strfry-compose.yml start strfry

# Off-site upload
rclone copy "${LOCAL_PATH}" remote:relay-backups/

# Prune local copies older than 14 days
find "${BACKUP_DIR}" -name 'strfry-*.tar.zst' -mtime +14 -delete

# Prune off-site copies older than 90 days
rclone delete --min-age 90d remote:relay-backups/
```

Cron entry:

```
# /etc/cron.d/strfry-backup
0 3 * * *  root  /usr/local/bin/strfry-backup.sh
```

The stop/copy/start window is ~5–10 seconds at v1 scale.

## Restore procedure

1. Stop strfry: `docker compose stop strfry`
2. `tar -I zstd -xf strfry-<date>.tar.zst -C /`
3. Start strfry: `docker compose up -d strfry`
4. Verify: subscribe with a Nostr client and confirm recent events
   are present

## Disaster recovery

Full host loss:

1. Provision a new VPS, point DNS at it
2. Restore Docker + Compose
3. `rclone copy remote:relay-backups/strfry-<latest>.tar.zst .`
4. Untar → restart compose
5. Caddy will obtain a new cert if the previous one's archive isn't
   restored; expect ~30s of downtime while it provisions

RPO: 24 hours (last nightly snapshot).
RTO: 30 minutes (provision + restore).

## Off-site checklist

- [ ] `rclone` credentials in `/root/.config/rclone/rclone.conf`
      with mode 600
- [ ] Off-site bucket has versioning enabled
- [ ] Off-site bucket is in a different geographic region from the VPS
- [ ] At least one quarterly restore drill — actually rehearse
      restoring to a fresh VPS
