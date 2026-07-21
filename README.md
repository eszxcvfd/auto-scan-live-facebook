# LiveScout

LiveScout is a local web app for discovering publicly searchable Facebook livestreams that are live at search time.

## Current scope

- Search requires at least one keyword or phrase.
- Browser automation visits public Facebook discovery pages only.
- The app does not automate login or access private content.
- Candidate results are opened and verified before they are returned.
- Recordings, replays, premieres, and ended videos are excluded.
- Results open on Facebook; the app does not replay or embed broadcasts.

Discovery coverage is best-effort. Facebook may change its UI, require CAPTCHA, rate-limit requests, or return incomplete public search results.

## Backend

```bash
uv sync --extra dev
uv run playwright install chromium
uv run uvicorn backend.app.main:app --reload --port 8000
```

Set `FACEBOOK_HEADLESS=false` when you need to see the discovery browser while diagnosing a failure.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>.
