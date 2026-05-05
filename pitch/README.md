# chaos pitch decks

Hermes-facing material. Use the short deck for the first conversation.

| Deck | Slides | Use |
|---|---:|---|
| `chaos-hermes-short.html` | 12 | First Hermes partnership meeting |

## View locally

Self-contained HTML, no build step:

```bash
open chaos-hermes-short.html        # macOS
xdg-open chaos-hermes-short.html    # Linux
start chaos-hermes-short.html       # Windows
```

Or serve the directory:

```bash
python3 -m http.server 8000
# visit http://localhost:8000/chaos-hermes-short.html
```

## Notes / PDF

- Speaker notes: append `?showNotes` or press `S`.
- PDF export: append `?print-pdf` and print from the browser.
- Static deploy: publish `pitch/` as-is. No build step.

## Files

- `chaos-hermes-short.html` — partnership deck.
- `assets/chaos-demo.mp4`, `assets/chaos-closing.mp4` — background
  videos used by the deck (title + closing slides).
- `legacy/` — archived deck fragments. **Frozen — do not link from
  current decks.** Kept for historical reference; uses pre-merger
  `seller`/`buyer` terminology that the current architecture has
  superseded (see `AGENTS.md` Rule 11).
- `.nojekyll` — flag for GitHub Pages to skip Jekyll processing.
- `README.md` — this file.
