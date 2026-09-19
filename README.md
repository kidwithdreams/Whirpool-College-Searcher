# Whirpool College Searcher

Find the college that suits you best. University profiles, campus photographs,
admissions guidance, and a responsive video landing page.

## Website

The frontend lives in `docs/` and is published with GitHub Pages from the
`main` branch, `/docs` folder. All asset paths support a repository subdirectory.

## Backend

GitHub Pages serves static files; it does not run AI requests or store API keys.
`server/index.js` contains the current Cloudflare-compatible backend for
`/api/search`, `/api/advice`, and `/api/gallery`.
`backend/` preserves the alternative Python FastAPI implementation; see its README.

The frontend's `API_BASE` in `docs/app.js` points to the separate API server.
That server must allow the GitHub Pages origin with CORS and be publicly reachable.
Configure `GEMINI_API_KEY`, `SEARCH_API_KEY`, and optionally
`SEARCH_API_KEY_FALLBACK` through the backend host's secret settings.
Never put credentials in frontend files, GitHub Pages, or source control.

## Local preview

Run `python -m http.server 8080 --directory docs` and open http://localhost:8080.
The API server must explicitly allow localhost if local API access is required.

## Repository safety

This repository starts with a fresh history. Real environment files, hosting
credentials, private work folders, and the original Git history are excluded.
`backend/.env.example` contains empty credential placeholders only.
