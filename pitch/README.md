# chaos pitch deck

A single-file Reveal.js slide deck for the Hermes team (Nous Research)
explaining what chaos is and why it matters as a Hermes-built
protocol.

## View locally

The deck is one self-contained HTML file with no build step. Open it
directly:

```bash
open chaos-deck.html        # macOS
xdg-open chaos-deck.html    # Linux
start chaos-deck.html       # Windows
```

Or serve it from this directory if you want clean URL routing for
Reveal's print / fragment behavior:

```bash
python3 -m http.server 8000
# then visit http://localhost:8000/chaos-deck.html
```

## Speaker view

Append `?showNotes` to the URL for the side-by-side notes pane:

```
chaos-deck.html?showNotes
```

Press `S` once the deck is open for the standalone speaker window
(requires popups enabled).

## Print to PDF

Append `?print-pdf` and use the browser's "Save as PDF" dialog at
A4 / Letter, no margins:

```
chaos-deck.html?print-pdf
```

## Deploy to GitHub Pages

This directory is gh-pages ready. Drop the whole `pitch/` folder into
the `gh-pages` branch (or the `docs/` folder of `main` if Pages is
configured that way). The `.nojekyll` file is already included so
Pages serves the assets raw without trying to run them through Jekyll.

```bash
git checkout --orphan gh-pages
git rm -rf .
cp pitch/* .
git add .
git commit -m "deploy pitch deck"
git push origin gh-pages
```

The deck will be reachable at
`https://<user>.github.io/<repo>/chaos-deck.html`.

## Deploy to any static host

It is a single HTML file plus an empty `.nojekyll` flag. Drop it into
Vercel, Netlify, Cloudflare Pages, S3+CloudFront, or `python -m
http.server` on a VPS. No backend.

## Files

- `chaos-deck.html` — the deck (Reveal.js v5.1.0 from CDN, all
  diagrams inline SVG, all styles inline)
- `.nojekyll` — flag for GitHub Pages to skip Jekyll processing
- `README.md` — this file
