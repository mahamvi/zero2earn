from fastapi import APIRouter, Form
from pathlib import Path
import sqlite3
from datetime import datetime

router = APIRouter(prefix="/api/admin", tags=["admin"])

DB_PATH = Path(__file__).resolve().parents[2] / "zero2earn.db"


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_tables():
    conn = db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS partner_leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        organization TEXT NOT NULL,
        lead_type TEXT DEFAULT 'partner',
        message TEXT DEFAULT '',
        created_at TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()


@router.get("/stats")
def admin_stats():
    ensure_tables()
    conn = db()
    cur = conn.cursor()

    def count(table):
        try:
            return cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        except Exception:
            return 0

    users = count("users")
    applications = count("applications")
    income = 0

    try:
        row = cur.execute("SELECT COALESCE(SUM(amount),0) FROM income").fetchone()
        income = row[0] or 0
    except Exception:
        income = 0

    leads = count("partner_leads")

    conn.close()

    return {
        "total_users": users,
        "total_applications": applications,
        "total_income": income,
        "partner_leads": leads,
        "pro_users": 0,
        "monthly_revenue": 0
    }


@router.post("/leads")
def create_lead(
    name: str = Form(...),
    email: str = Form(...),
    organization: str = Form(...),
    lead_type: str = Form("partner"),
    message: str = Form("")
):
    ensure_tables()
    conn = db()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO partner_leads
    (name, email, organization, lead_type, message, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        name,
        email,
        organization,
        lead_type,
        message,
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()

    return {"ok": True, "message": "Lead saved"}


@router.get("/leads")
def list_leads():
    ensure_tables()
    conn = db()
    rows = conn.execute("""
        SELECT * FROM partner_leads
        ORDER BY id DESC
    """).fetchall()
    conn.close()

    return {
        "items": [dict(r) for r in rows]
    }


@router.get("/users")
def list_users():
    conn = db()
    try:
        rows = conn.execute("""
            SELECT id, name, email, headline, track, stage, goal_daily
            FROM users
            ORDER BY id DESC
        """).fetchall()
        users = [dict(r) for r in rows]
    except Exception:
        users = []
    conn.close()

    return {"items": users}