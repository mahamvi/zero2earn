# Zero2Earn V2 Automation Engine

Run:
```bat
cd C:\Users\LN\Desktop\zero2earn_full
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python seed_data.py
python -m uvicorn zero2earn_backend.api.app:app --reload
```

Open: http://127.0.0.1:8000

Demo login:
- demo@zero2earn.ai
- demo123

Automation Engine includes:
- Daily Mode
- auto-prepare application queue
- follow-up generator
- follow-up sent tracking
- income forecast
- application streak
- connected Automation tab, Applications, RM, and Home.
