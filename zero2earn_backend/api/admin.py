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
        status TEXT DEFAULT 'new',
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

    def sum_payments():
        try:
            row = cur.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='paid'").fetchone()
            return int((row[0] or 0) / 100)
        except Exception:
            return 0

    total_users = count("users")
    total_applications = count("applications")
    partner_leads = count("partner_leads")
    revenue = sum_payments()

    try:
        pro_users = cur.execute("SELECT COUNT(*) FROM users WHERE plan='pro'").fetchone()[0]
    except Exception:
        pro_users = 0

    try:
        income = cur.execute("SELECT COALESCE(SUM(amount),0) FROM income").fetchone()[0] or 0
    except Exception:
        income = 0

    conversion = round((pro_users / total_users) * 100, 1) if total_users else 0

    conn.close()

    return {
        "total_users": total_users,
        "pro_users": pro_users,
        "free_users": max(total_users - pro_users, 0),
        "total_applications": total_applications,
        "total_income": income,
        "partner_leads": partner_leads,
        "monthly_revenue": revenue,
        "mrr": revenue,
        "arpu": round(revenue / total_users, 1) if total_users else 0,
        "conversion_rate": conversion
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

    conn.execute("""
    INSERT INTO partner_leads
    (name, email, organization, lead_type, message, status, created_at)
    VALUES (?, ?, ?, ?, ?, 'new', ?)
    """, (name, email, organization, lead_type, message, datetime.now().isoformat(timespec="seconds")))

    conn.commit()
    conn.close()

    return {"ok": True, "message": "Lead saved"}


@router.get("/leads")
def list_leads():
    ensure_tables()
    conn = db()
    rows = conn.execute("SELECT * FROM partner_leads ORDER BY id DESC").fetchall()
    conn.close()
    return {"items": [dict(r) for r in rows]}


@router.get("/users")
def list_users():
    conn = db()
    try:
        rows = conn.execute("""
            SELECT id, name, email, headline, track, stage, goal_daily, plan, pro_until
            FROM users
            ORDER BY id DESC
        """).fetchall()
        users = [dict(r) for r in rows]
    except Exception:
        users = []
    conn.close()
    return {"items": users}


@router.get("/payments")
def list_payments():
    conn = db()
    try:
        rows = conn.execute("""
            SELECT * FROM payments
            ORDER BY id DESC
        """).fetchall()
        items = [dict(r) for r in rows]
        for item in items:
            item["amount_rupees"] = int((item.get("amount") or 0) / 100)
    except Exception:
        items = []
    conn.close()
    return {"items": items}