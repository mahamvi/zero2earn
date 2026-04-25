#!/usr/bin/env bash
set -e
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python seed_data.py
python -m uvicorn zero2earn_backend.api.app:app --reload
