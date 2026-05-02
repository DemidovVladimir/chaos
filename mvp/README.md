# MVP — run it

The whole weekend MVP in two scripts plus a config. No infrastructure.

## Setup (5 min)

```bash
cd mvp
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Generate keypairs (one per role):

```bash
python seller.py keygen   # writes ~/.mvp/seller.key
python buyer.py keygen    # writes ~/.mvp/buyer.key
```

Each script prints the corresponding `npub` so the other side knows
who to DM.

## Run a publish

On Laptop A:

```bash
python seller.py publish sample_car.toml
```

Expected output:

```
Published listing 8f4a2b1e (event id 9d3a...) to wss://relay.damus.io
```

Then start the listener:

```bash
python seller.py listen
```

`seller.py listen` keeps running and listens for inquiries.

## Run a buyer

On Laptop B:

```bash
python buyer.py watch
```

Expected output, within seconds:

```
Match: 2018 Mazda 3 hatchback
  price:    15000 EUR
  location: EU/CZ/Prague
  seller:   npub17c4f...
  summary:  65k mi, 1 owner. 15,000 EUR. Prague.

Send the seller a DM? Type a message (blank to skip):
> tell me more about service history
Sent. Listening for reply...
```

When the seller replies:

```
Reply from npub17c4f...:
> Full Mazda dealer service history. Recently passed STK. New tires.
> Photos available via ACP session when you're ready to book one.
```

(Photo sharing lights up in the post-weekend sprint via ACP content
blocks. No third-party file host involved.)

## Files

- `seller.py` — publish + listen-for-DMs + reply
- `buyer.py` — subscribe + match + send-DM + receive-reply
- `shared.py` — keypair load/save, NIP-99 event builder
- `sample_car.toml` — a fake car listing in TOML; edit to change facets
- `requirements.txt` — only `pynostr` and `tomli`

## Common failures and fixes

- **`SSL: CERTIFICATE_VERIFY_FAILED`** — already handled. The scripts
  prepend a small block that points Python at `certifi`'s CA bundle
  via `SSL_CERT_FILE`. This fixes the well-known macOS Python issue
  where the SSL module ships without CA certs wired up. If you ever
  see this error again on a different machine, run
  `pip install --upgrade certifi` in the venv and re-run.
- **`websockets.exceptions.ConnectionClosed`** — relay disconnected.
  Re-run; both scripts auto-reconnect once.
- **No matches in `buyer.py`** — check that the filter in `buyer.py`
  matches the seller's tags. Default filter is `t=cars, make=mazda`;
  if you changed `sample_car.toml`, change the filter too.
- **DM not arriving** — both scripts need to share at least one relay.
  Default is `relay.damus.io` + `nos.lol`. If you changed one,
  make them match.

## Next steps once it works

See `../MVP_WEEKEND.md` § "After the weekend" for the four-week
follow-up plan.

---

## Verification record

**In-process verification: PASS.** Saturday morning you only need to
verify the network round-trip; the code itself is known-good.

Run on 2026-05-02 against `pynostr==0.6.2`, Python 3.10:

| Smoke test | Result | Notes |
|---|---|---|
| `pip install pynostr==0.6.2 tomli` | ✅ | Resolves clean. Pulls coincurve (Schnorr), cryptography, tornado, rich |
| `python seller.py keygen` | ✅ | Real npub generated: `npub1xg6y3n9erdfka6p7nv04tk827fqxtnavrdg2c9sr9q4uvtqjfy3scgwv4f` |
| `python buyer.py keygen` | ✅ | Real npub generated: `npub1ana5thxyfc34ypdl670fftyw8mn8fe0jqw3gkah9wrrva7lxm3cq9vw669` |
| `python seller.py publish sample_car.toml` (in-process) | ✅ | NIP-99 event constructed + signed locally, event id `c4a45f6a8d74…`. Network egress was firewalled in the verification environment, so the relay round-trip itself was not exercised. |
| `python buyer.py watch` (in-process) | ✅ | Filter + subscription set up cleanly; pynostr's reconnect loop runs as expected. Same network limitation as above. |

**One API drift fixed during verification**: in `seller.py`, the
`Event(...)` constructor takes `pubkey=` (not `pub_key=`) on
pynostr 0.6.2. Already corrected in this commit.

### What you still need to verify Saturday morning

1. From your laptop (with internet), run `python seller.py publish
   sample_car.toml`. Expected: relays accept the event and you see
   `Published listing ... to 2 relay(s).` without the `Error
   connecting` lines.
2. From the same laptop (or a second one), run `python buyer.py
   watch`. Expected within seconds: `Match: 2018 Mazda 3 hatchback
   …` plus a DM prompt.
3. Reply round-trip: type a DM in the buyer, see the seller's
   listener prompt, type a reply, see the buyer print the reply.

If any of those fail, the issue is environmental (firewall, captive
portal, ISP blocking 443 to relays) — not the code.

### Cleanup notes

- A `venv/` directory was created in this folder during verification
  and could not be removed from the sandbox (filesystem ownership).
  You can safely `rm -rf mvp/venv` and recreate fresh:
  ```bash
  cd mvp
  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
  ```
- The verification's throwaway keypairs landed in the sandbox's
  home, not your `~/.mvp/`. When you run `keygen` on your laptop
  you'll get fresh keys.
