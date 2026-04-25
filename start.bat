@echo off
python -m venv venv
call venv\Scripts\activate
pip install -r requirements.txt
python seed_data.py
python -m uvicorn zero2earn_backend.api.app:app --reload
