# chaos pitch decks

Hermes-facing decks. Use the short deck for the first conversation;
keep the depth deck as backup.

| Deck | Slides | Use |
|---|---:|---|
| `chaos-hermes-short.html` | 12 | First Hermes partnership meeting |
| `chaos-deck.html` | 14 | Longer technical follow-up |

## View locally

The decks are self-contained HTML files with no build step. Open
either directly:

```bash
open chaos-hermes-short.html   # macOS — short deck (default)
open chaos-deck.html           # macOS — depth deck

xdg-open chaos-hermes-short.html   # Linux
start chaos-hermes-short.html      # Windows
```

Or serve this directory:

```bash
python3 -m http.server 8000
# then visit http://localhost:8000/chaos-hermes-short.html
```

## Notes / PDF

- Speaker notes: append `?showNotes` or press `S`.
- PDF export: append `?print-pdf` and print from the browser.
- Static deploy: publish the `pitch/` directory as-is. No build step.

## Files

- `chaos-hermes-short.html` — default partnership deck.
- `chaos-deck.html` — depth deck.
- `assets/chaos-demo.mp4`, `assets/chaos-closing.mp4` — background
  videos for the short deck.
- `.nojekyll` — flag for GitHub Pages to skip Jekyll processing.
- `README.md` — this file.
