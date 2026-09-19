# GitHub Pages frontend

This folder is the public, static frontend served by GitHub Pages.

- `index.html` contains the semantic landing-page structure.
- `styles.css` implements the responsive liquid-glass design and animations.
- `app.js` handles the morphing search panel, university profiles, the AI advisor,
  gallery filters, and incremental image loading.
- `assets/` contains the hero video, graduate cut-outs, sample campus visuals, and
  the Whirpool logo.

The browser calls the public serverless API through `API_BASE` in `app.js`. No API
keys are present in this folder; all provider credentials remain server-side.

For a quick local preview:

```powershell
python -m http.server 8080 --directory docs
```

Then open `http://localhost:8080`. API requests from localhost require the backend
to allow that origin.
