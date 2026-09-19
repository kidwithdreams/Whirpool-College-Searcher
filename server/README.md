# Production serverless API

`index.js` is the backend used by the deployed GitHub Pages website. It exposes:

| Route | Method | Purpose |
| --- | --- | --- |
| `/api/search` | `POST` | Build a university profile from a university name |
| `/api/advice` | `POST` | Recommend universities from a natural-language student profile |
| `/api/gallery` | `GET` | Load five additional university images for a selected category |

The worker runs independent data operations concurrently, calls Gemini for concise
summaries and recommendations, uses Serper for image discovery, and uses public
Wikipedia and OpenStreetMap/Nominatim data for context and location signals.

Required server-side secrets:

- `GEMINI_API_KEY`
- `SEARCH_API_KEY`
- optional `SEARCH_API_KEY_FALLBACK`

`GEMINI_MODEL` and `SEARCH_API_URL` are configurable. Credentials are supplied by
the host as environment variables and must never be added to frontend files.

The worker accepts cross-origin API requests from
`https://kidwithdreams.github.io`, allowing the static GitHub Pages frontend to use
the API while keeping provider keys off the client.
