# Zero2Earn AI — SaaS Deploy Build

Zero2Earn is a resume-first AI job acquisition and income engine. This package is ready for local use and simple cloud deployment.

## Local run

```bat
cd zero2earn_full
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python seed_data.py
python -m uvicorn zero2earn_backend.api.app:app --reload
```

Open: http://127.0.0.1:8000

Demo login: demo@zero2earn.ai / demo123

## SaaS user flow

1. Create account
2. Paste/upload resume in Resume First
3. Optimize resume layer
4. Review matched jobs
5. Use Wingman / Apply Engine
6. Track replies and follow-ups
7. Use Automation daily

## Render deployment

1. Push this folder to GitHub.
2. Create a new Render web service.
3. Use the included `render.yaml` or set:
   - Build: `pip install -r requirements.txt`
   - Start: `python seed_data.py && uvicorn zero2earn_backend.api.app:app --host 0.0.0.0 --port $PORT`
4. Add a persistent disk mounted at `/var/data`.
5. Set env vars:
   - `APP_ENV=production`
   - `DATA_DIR=/var/data`
   - `DATABASE_PATH=/var/data/zero2earn.db`

## Railway deployment

1. Push to GitHub.
2. Create Railway project from repo.
3. Railway uses `railway.json`.
4. Add persistent storage if available, or set `DATA_DIR=/data`.

## Docker deployment

```bash
docker build -t zero2earn-ai .
docker run -p 8000:8000 -v zero2earn_data:/data --env-file .env.example zero2earn-ai
```

## What is production-ready in this build

- Multi-user signup
- Password hashing for new users
- Resume-first flow
- Resume optimization
- Job matching
- Wingman proposals
- Apply Engine
- Skill Engine
- Tracking Engine
- Automation Engine
- Health endpoint: `/health`
- Render/Railway/Docker deployment files
- Persistent SQLite path via env vars

## Before paid launch

Add:
- domain + HTTPS
- privacy policy and terms
- Razorpay/Stripe billing
- email verification
- automated database backups
- admin dashboard
