# Whirlpool FastAPI backend

> This directory is a documented Python reference implementation of the profiling
> pipeline. The deployed hackathon website currently uses the lighter serverless
> worker in [`../server/index.js`](../server/index.js), which provides the search,
> advisor, and gallery endpoints used by GitHub Pages.

This service implements the three concurrent streams behind the Whirlpool campus
profiler. `POST /api/search` runs image retrieval/verification, summary generation,
and location metadata concurrently under a 29-second request deadline.

## Run locally

Python 3.11+ is recommended.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit backend/.env and add fresh keys. Never commit this file.
uvicorn app.main:app --reload --port 8000
```

Test the endpoint:

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/search `
  -ContentType application/json `
  -Body '{"university_name":"Nazarbayev University"}'
```

Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

## Environment

Required:

- Either `GEMINI_API_KEY`, or both `YANDEX_API_KEY` and `YANDEX_FOLDER_ID`
- `SEARCH_API_KEY`

Optional: `SEARCH_API_KEY_FALLBACK` adds round-robin distribution and automatic
failover for authentication or quota errors across two Serper keys.

The search adapter expects Serper's image API response shape and defaults to
`https://google.serper.dev/images`. Change `SEARCH_API_URL` or the small adapter in
`app/services/images.py` when using another provider.

`gemini-1.5-flash` was shut down on September 29, 2025. The sample configuration
therefore uses `gemini-3.5-flash-lite`, which supports minimal thinking and produces
complete short summaries inside the required 120-token ceiling. `GEMINI_MODEL`
remains configurable.
Set `AI_PROVIDER=yandex` to use YandexGPT instead. Its model URI is assembled as
`gpt://<YANDEX_FOLDER_ID>/<YANDEX_MODEL>/latest` and requests use Yandex AI Studio's
OpenAI-compatible endpoint.

## Pipeline behavior

- Four image searches start together. Images are protected against private-network
  downloads, capped at 8 MB, exact-deduplicated with pHash, then near-deduplicated
  with normalized OpenCLIP ViT-B/32 embeddings at cosine similarity `> 0.90`.
- The same CLIP embeddings assign one of five zero-shot categories. If model weights
  are unavailable, the response degrades to transparent keyword categorization and
  `/health` reports `clip_ready: false`.
- Wikipedia and DuckDuckGo context are fetched concurrently, then summarized by
  Gemini with `max_output_tokens=120`. A source-text fallback is returned if Gemini
  is unavailable.
- Nominatim requests are cached, serialized, identified with a custom User-Agent,
  and rate-limited to at most one request per second. The public endpoint is suitable
  only for light hackathon traffic; use a hosted provider or self-hosted Nominatim in
  production, retain attribution, and follow its usage policy.
- Climate and living-cost values are explicitly approximate heuristics, not live
  measurements or financial advice.

The first process start may download OpenCLIP weights. Warm the process before a demo
so that model initialization is outside the 30-second request budget.

## Tests

```powershell
cd backend
pytest -q
```
