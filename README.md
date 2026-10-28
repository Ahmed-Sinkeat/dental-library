# Dr. Ahmed Badr — Dental Library

**Live:** https://dental-library.sinkeat-lab.workers.dev/ar/

A bilingual (Arabic RTL / English LTR) library for a dentist's Telegram teaching channel: 456 lectures, slides, PDFs and videos organized into 20 subjects and 52 topics, with search, subject/format filters and in-browser playback.

## How it works

- **Import:** `catalog.py` classifies every channel file into subject/topic (`catalog.csv`); `compress.py` re-encodes audio to Opus before upload to Cloudflare R2.
- **Site:** Astro static build (`src/`), Arabic and English routes; filters and search preserved across language switches.
- **Media:** a small Cloudflare Worker (`site/src/worker.js`) streams files from a private R2 bucket with HTTP Range support, so audio and video seek without downloading.

```sh
npm install
npm run dev      # local site
npm test         # catalog tests
npm run build
cd site && npx wrangler deploy
```

Media files are not in this repository; they live in R2.
