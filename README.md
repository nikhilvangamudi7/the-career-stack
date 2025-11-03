# The Career Stack

Live-first job discovery: front-end (Vercel) + backend FastAPI (Render) + GitHub Actions generating companies.csv daily.

## Quick start (cloud)
1. Deploy backend (Render) connecting to this repo's `backend/` folder (Dockerfile present).  
2. Deploy frontend (Vercel) pointing to `frontend/`. Set env var `NEXT_PUBLIC_BACKEND_URL` to your Render backend URL.  
3. (Optional) Open GitHub Codespaces to edit files live.

## GitHub Actions
`.github/workflows/daily-scrape.yml` regenerates `backend/companies.csv` daily and commits.

## Telegram (optional)
Set `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID` as env vars in Render to use `/api/send-telegram`.

