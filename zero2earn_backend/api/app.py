from fastapi import FastAPI, Form, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from datetime import datetime, timedelta
import sqlite3
import re
import os
import hmac
import hashlib

try:
    import razorpay
except Exception:
    razorpay = None

from . import admin

app = FastAPI(title="Zero2Earn AI SaaS", version="2.1.0")
app.include_router(admin.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "zero2earn.db"

RAZORPAY_KEY = os.getenv("RAZORPAY_KEY", "")
RAZORPAY_SECRET = os.getenv("RAZORPAY_SECRET", "")
PRO_PRICE_INR = int(os.getenv("PRO_PRICE_INR", "499"))


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def now():
    return datetime.now().isoformat(timespec="seconds")


def add_column_if_missing(cur, table, column, definition):
    cols = [r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in cols:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db():
    conn = db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT,
        headline TEXT DEFAULT '',
        summary TEXT DEFAULT '',
        skills TEXT DEFAULT '',
        resume_text TEXT DEFAULT '',
        track TEXT DEFAULT 'Resume first',
        stage TEXT DEFAULT 'Zero',
        goal_daily INTEGER DEFAULT 500,
        plan TEXT DEFAULT 'free',
        pro_until TEXT DEFAULT '',
        razorpay_payment_id TEXT DEFAULT '',
        razorpay_order_id TEXT DEFAULT '',
        created_at TEXT DEFAULT ''
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        task_type TEXT,
        title TEXT,
        description TEXT,
        estimated_reward INTEGER DEFAULT 0,
        priority INTEGER DEFAULT 5,
        status TEXT DEFAULT 'pending',
        linked_job_id TEXT DEFAULT '',
        created_at TEXT DEFAULT ''
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        job_id TEXT,
        title TEXT,
        company TEXT,
        link TEXT,
        score INTEGER DEFAULT 0,
        status TEXT DEFAULT 'prepared',
        notes TEXT DEFAULT '',
        created_at TEXT DEFAULT '',
        updated_at TEXT DEFAULT ''
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS income (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount INTEGER,
        source TEXT,
        note TEXT DEFAULT '',
        created_at TEXT DEFAULT ''
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        message TEXT,
        created_at TEXT DEFAULT ''
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        razorpay_order_id TEXT,
        razorpay_payment_id TEXT DEFAULT '',
        amount INTEGER,
        currency TEXT DEFAULT 'INR',
        status TEXT DEFAULT 'created',
        created_at TEXT DEFAULT ''
    )
    """)

    # Safe migrations for old DB files
    for col, definition in {
        "skills": "TEXT DEFAULT ''",
        "resume_text": "TEXT DEFAULT ''",
        "plan": "TEXT DEFAULT 'free'",
        "pro_until": "TEXT DEFAULT ''",
        "razorpay_payment_id": "TEXT DEFAULT ''",
        "razorpay_order_id": "TEXT DEFAULT ''",
        "created_at": "TEXT DEFAULT ''"
    }.items():
        add_column_if_missing(cur, "users", col, definition)

    for col, definition in {
        "user_id": "INTEGER",
        "task_type": "TEXT DEFAULT ''",
        "estimated_reward": "INTEGER DEFAULT 0",
        "priority": "INTEGER DEFAULT 5",
        "linked_job_id": "TEXT DEFAULT ''",
        "created_at": "TEXT DEFAULT ''"
    }.items():
        add_column_if_missing(cur, "tasks", col, definition)

    for col, definition in {
        "user_id": "INTEGER",
        "job_id": "TEXT DEFAULT ''",
        "title": "TEXT DEFAULT ''",
        "company": "TEXT DEFAULT ''",
        "link": "TEXT DEFAULT ''",
        "score": "INTEGER DEFAULT 0",
        "notes": "TEXT DEFAULT ''",
        "created_at": "TEXT DEFAULT ''",
        "updated_at": "TEXT DEFAULT ''"
    }.items():
        add_column_if_missing(cur, "applications", col, definition)

    for col, definition in {
        "user_id": "INTEGER",
        "source": "TEXT DEFAULT 'Manual'",
        "note": "TEXT DEFAULT ''",
        "created_at": "TEXT DEFAULT ''"
    }.items():
        add_column_if_missing(cur, "income", col, definition)

    conn.commit()
    conn.close()


init_db()


def add_alert(user_id: int, message: str):
    conn = db()
    conn.execute(
        "INSERT INTO alerts (user_id, message, created_at) VALUES (?, ?, ?)",
        (user_id, message, now())
    )
    conn.commit()
    conn.close()


def ensure_user_tasks(user_id: int):
    conn = db()
    cur = conn.cursor()
    count = cur.execute("SELECT COUNT(*) FROM tasks WHERE user_id=?", (user_id,)).fetchone()[0]

    if count == 0:
        tasks = [
            ("apply", "Submit 5 prepared applications", "Apply to jobs", 500, 10),
            ("track", "Update application statuses", "Track pipeline", 0, 9),
            ("micro", "Complete one microjob", "Earn fast", 100, 8),
            ("skill", "Fix one skill gap", "Improve profile", 0, 7),
        ]

        for task_type, title, desc, reward, priority in tasks:
            cur.execute("""
            INSERT INTO tasks
            (user_id, task_type, title, description, estimated_reward, priority, status, linked_job_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'pending', '', ?)
            """, (user_id, task_type, title, desc, reward, priority, now()))

    conn.commit()
    conn.close()


def user_profile(user_id: int):
    conn = db()
    row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    d = dict(row)
    d.pop("password", None)
    d["skills"] = [s.strip() for s in (d.get("skills") or "").split(",") if s.strip()]
    return d


def extract_resume_text(raw: str):
    text = re.sub(r"\s+", " ", raw or "").strip()
    lowered = text.lower()

    skills = []
    for kw in [
        "Medical Writing", "Clinical Research", "Healthcare Consulting",
        "Telemedicine", "Research", "Documentation", "AI Tools",
        "Patient Education", "Clinical Operations", "Content Writing",
        "Data Analysis"
    ]:
        if kw.lower() in lowered:
            skills.append(kw)

    if not skills:
        skills = ["Medical Writing", "Research", "Documentation"]

    track = "Medical writing + AI + consulting"

    missing = []
    for kw in ["Portfolio", "LinkedIn", "Writing Samples"]:
        if kw.lower() not in lowered:
            missing.append(kw)

    headline = f"Dr Ramesh | {track} | {', '.join(skills[:3])}"
    summary = (
        f"Profile focus: {track}. Key strengths: {', '.join(skills[:5])}. "
        "This profile is positioned for remote healthcare, research, content, "
        "documentation, and AI-assisted consulting opportunities."
    )

    return {
        "skills": skills,
        "track": track,
        "missing_keywords": missing,
        "headline": headline,
        "summary": summary,
        "resume_text": text,
        "resume_score": min(95, 55 + len(skills) * 5),
        "optimized_headline": headline,
        "optimized_summary": summary,
        "recommended_bullets": [
            f"Built experience around {', '.join(skills[:3])} with structured execution and measurable contribution.",
            "Improved workflow quality through documentation, communication, and reliable task completion.",
            "Adapted quickly to remote work requirements, tools, deadlines, and outcome-focused delivery."
        ],
        "ats_keywords": skills + missing,
        "job_search_focus": [
            "medical writer",
            "research assistant",
            "documentation specialist",
            "healthcare consultant"
        ]
    }


LIVE_JOBS = [
    {
        "id": "medical-writer-001",
        "title": "Medical Content Writer",
        "company": "Remote Healthcare Studio",
        "location": "Remote",
        "source": "Zero2Earn curated",
        "apply_url": "https://www.linkedin.com/jobs/search/?keywords=medical%20writer%20remote",
        "keywords": "medical writing healthcare clinical research documentation content"
    },
    {
        "id": "clinical-research-002",
        "title": "Clinical Research Assistant",
        "company": "Health Research Network",
        "location": "Remote",
        "source": "Zero2Earn curated",
        "apply_url": "https://www.indeed.com/jobs?q=clinical+research+assistant+remote",
        "keywords": "clinical research healthcare documentation data patient"
    },
    {
        "id": "insurance-verification-003",
        "title": "Insurance Verification Specialist",
        "company": "Healthcare Operations Co",
        "location": "Remote",
        "source": "Zero2Earn curated",
        "apply_url": "https://www.indeed.com/jobs?q=insurance+verification+remote",
        "keywords": "healthcare insurance verification documentation claims"
    },
    {
        "id": "patient-education-004",
        "title": "Patient Education Content Specialist",
        "company": "Digital Health Academy",
        "location": "Remote",
        "source": "Zero2Earn curated",
        "apply_url": "https://www.linkedin.com/jobs/search/?keywords=patient%20education%20content%20remote",
        "keywords": "patient education medical writing healthcare content"
    }
]


MICROJOBS = [
    {
        "id": "clickworker",
        "name": "Clickworker",
        "category": "Microtasks",
        "payout_speed": "Medium",
        "earning_range": "Rs.200-Rs.1,500/day",
        "url": "https://www.clickworker.com/clickworker-job/",
        "why": "Quick-start platform for surveys, writing, categorization, and web research."
    },
    {
        "id": "toloka",
        "name": "Toloka",
        "category": "AI data tasks",
        "payout_speed": "Fast",
        "earning_range": "Rs.150-Rs.1,000/day",
        "url": "https://toloka.ai/tolokers/",
        "why": "Useful for annotation, search relevance, and small AI evaluation tasks."
    },
    {
        "id": "oneforma",
        "name": "OneForma",
        "category": "AI projects",
        "payout_speed": "Medium",
        "earning_range": "Rs.300-Rs.3,000/day",
        "url": "https://jobs.oneforma.com/",
        "why": "Better for language, annotation, and long-running AI data projects."
    }
]


def score_job(user, job):
    text = (
        (user.get("headline") or "") + " " +
        (user.get("summary") or "") + " " +
        " ".join(user.get("skills") or [])
    ).lower()

    keywords = job["keywords"].lower().split()
    hits = sum(1 for k in keywords if k in text)

    score = min(95, 20 + hits * 12)

    if "medical" in job["keywords"] and "medical" in text:
        score += 10
    if "research" in job["keywords"] and "research" in text:
        score += 8
    if "documentation" in job["keywords"] and "documentation" in text:
        score += 6

    return min(95, score)


@app.get("/")
def home():
    return {"message": "Zero2Earn API v2 running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/signup")
def signup(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    goal_daily: int = Form(500)
):
    conn = db()
    try:
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO users
        (name, email, password, goal_daily, plan, created_at)
        VALUES (?, ?, ?, ?, 'free', ?)
        """, (name, email, password, goal_daily, now()))
        user_id = cur.lastrowid
        conn.commit()
        ensure_user_tasks(user_id)
        add_alert(user_id, "Welcome to Zero2Earn. Start by uploading your resume.")
        return {"user_id": user_id, "email": email}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Email already registered")
    finally:
        conn.close()


@app.post("/api/login")
def login(email: str = Form(...), password: str = Form(...)):
    conn = db()
    user = conn.execute(
        "SELECT * FROM users WHERE email=? AND password=?",
        (email, password)
    ).fetchone()
    conn.close()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid login")

    ensure_user_tasks(user["id"])
    return {"user_id": user["id"], "email": user["email"]}


@app.get("/api/dashboard/{user_id}")
def dashboard(user_id: int):
    ensure_user_tasks(user_id)
    user = user_profile(user_id)

    conn = db()
    cur = conn.cursor()

    income_total = cur.execute(
        "SELECT COALESCE(SUM(amount),0) FROM income WHERE user_id=?",
        (user_id,)
    ).fetchone()[0]

    apps = cur.execute(
        "SELECT * FROM applications WHERE user_id=?",
        (user_id,)
    ).fetchall()

    tasks = cur.execute(
        "SELECT * FROM tasks WHERE user_id=? ORDER BY priority DESC",
        (user_id,)
    ).fetchall()

    alerts = cur.execute(
        "SELECT message, created_at FROM alerts WHERE user_id=? ORDER BY id DESC LIMIT 5",
        (user_id,)
    ).fetchall()

    total = len(apps)
    prepared = len([a for a in apps if a["status"] == "prepared"])
    applied = len([a for a in apps if a["status"] == "applied"])
    replied = len([a for a in apps if a["status"] == "replied"])
    interviews = len([a for a in apps if a["status"] == "interview"])
    hired = len([a for a in apps if a["status"] == "hired"])
    rejected = len([a for a in apps if a["status"] == "rejected"])

    reply_rate = round((replied / applied) * 100, 1) if applied else 0
    interview_rate = round((interviews / applied) * 100, 1) if applied else 0
    hire_rate = round((hired / applied) * 100, 1) if applied else 0
    rejection_rate = round((rejected / applied) * 100, 1) if applied else 0

    conn.close()

    return {
        "user": user,
        "metrics": {
            "total_earned": income_total,
            "jobs_applied": applied,
            "prepared": prepared,
            "replies": replied,
            "interviews": interviews,
            "win_rate": hire_rate,
            "reply_rate": reply_rate,
            "interview_rate": interview_rate,
            "hire_rate": hire_rate,
            "today_target": user["goal_daily"],
            "pending_tasks": len([t for t in tasks if t["status"] == "pending"]),
            "done_tasks": len([t for t in tasks if t["status"] == "done"])
        },
        "tracking": {
            "total": total,
            "prepared": prepared,
            "applied": applied,
            "viewed": len([a for a in apps if a["status"] == "viewed"]),
            "replied": replied,
            "interview": interviews,
            "hired": hired,
            "rejected": rejected,
            "reply_rate": reply_rate,
            "interview_rate": interview_rate,
            "hire_rate": hire_rate,
            "rejection_rate": rejection_rate,
            "avg_score": round(sum([a["score"] or 0 for a in apps]) / total, 1) if total else 0,
            "insights": [
                "Start by preparing 10 high-score applications, submitting 5 today, and tracking every response."
            ]
        },
        "tasks": [dict(t) for t in tasks],
        "alerts": [dict(a) for a in alerts]
    }


@app.post("/api/tasks/{task_id}/complete")
def complete_task(task_id: int):
    conn = db()
    cur = conn.cursor()
    task = cur.execute("SELECT user_id FROM tasks WHERE id=?", (task_id,)).fetchone()
    cur.execute("UPDATE tasks SET status='done' WHERE id=?", (task_id,))
    conn.commit()
    conn.close()

    if task:
        add_alert(task["user_id"], "Task completed. Momentum increased.")

    return {"ok": True}


@app.post("/api/profile/save/{user_id}")
def save_profile(
    user_id: int,
    headline: str = Form(...),
    summary: str = Form(...),
    skills: str = Form("")
):
    conn = db()
    conn.execute(
        "UPDATE users SET headline=?, summary=?, skills=? WHERE id=?",
        (headline, summary, skills, user_id)
    )
    conn.commit()
    conn.close()
    add_alert(user_id, "Profile updated successfully.")
    return {"ok": True}


@app.post("/api/resume/upload/{user_id}")
async def resume_upload(user_id: int, file: UploadFile = File(...)):
    raw = await file.read()
    text = raw.decode("utf-8", errors="ignore") or file.filename or "Uploaded resume"
    result = extract_resume_text(text)

    conn = db()
    conn.execute("""
    UPDATE users SET headline=?, summary=?, skills=?, resume_text=?, track=? WHERE id=?
    """, (
        result["headline"],
        result["summary"],
        ", ".join(result["skills"]),
        result["resume_text"],
        result["track"],
        user_id
    ))
    conn.commit()
    conn.close()

    add_alert(user_id, f"Resume uploaded and analyzed. Score {result['resume_score']}.")
    return result


@app.post("/api/resume/optimize/{user_id}")
def resume_optimize(user_id: int):
    user = user_profile(user_id)
    result = extract_resume_text(
        user.get("resume_text") or user.get("headline", "") + " " + user.get("summary", "")
    )

    conn = db()
    conn.execute("""
    UPDATE users SET headline=?, summary=?, skills=?, track=? WHERE id=?
    """, (
        result["headline"],
        result["summary"],
        ", ".join(result["skills"]),
        result["track"],
        user_id
    ))
    conn.commit()
    conn.close()

    add_alert(user_id, f"Resume optimized. Score {result['resume_score']} and focus updated.")
    return result


@app.get("/api/resume/status/{user_id}")
def resume_status(user_id: int):
    user = user_profile(user_id)
    return extract_resume_text(
        user.get("resume_text") or user.get("headline", "") + " " + user.get("summary", "")
    )


@app.get("/api/jobs/{user_id}")
def jobs(user_id: int, query: str = "", min_score: int = 0):
    user = user_profile(user_id)
    q = (query or "").lower()
    items = []

    for job in LIVE_JOBS:
        if q and q not in (job["title"] + " " + job["keywords"]).lower():
            continue

        score = score_job(user, job)

        if score < min_score:
            continue

        items.append({
            **job,
            "match_score": score,
            "win_probability": max(20, min(85, score - 5)),
            "apply_link": job["apply_url"]
        })

    items.sort(key=lambda x: x["match_score"], reverse=True)
    return {"jobs": items}


@app.get("/api/wingman/{user_id}")
def wingman(user_id: int, job_id: str):
    user = user_profile(user_id)
    job = next((j for j in LIVE_JOBS if j["id"] == job_id), None)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    score = score_job(user, job)

    proposal = f"""Hi {job['company']} team,

I’m interested in the {job['title']} role because it aligns with my background in {', '.join(user.get('skills', [])[:4])}.

My profile: {user.get('headline')}

I can contribute through clear documentation, research-backed work, reliable communication, and structured delivery.

Best regards"""

    return {
        "job_id": job_id,
        "title": job["title"],
        "company": job["company"],
        "portal_url": job["apply_url"],
        "match_score": score,
        "win_probability": max(20, min(85, score - 5)),
        "checklist": [
            "Open the source portal and review the full description.",
            "Keep the first 2 lines specific to the job title.",
            "Use strongest matched skills from your resume.",
            "Submit application and mark it applied."
        ],
        "proposal": proposal
    }


@app.get("/api/micro-jobs/{user_id}")
def micro_jobs(user_id: int):
    return {"items": MICROJOBS}


@app.get("/api/skills/{user_id}")
def skills(user_id: int):
    user = user_profile(user_id)
    needed = ["Portfolio", "LinkedIn", "Writing Samples", "Proposal Writing", "Remote Communication"]
    return {
        "items": [
            {
                "id": n.lower().replace(" ", "-"),
                "title": n,
                "description": f"Add or improve {n} to increase match quality."
            }
            for n in needed
        ],
        "current_skills": user.get("skills", [])
    }


@app.post("/api/applications/{user_id}")
def create_application(
    user_id: int,
    job_id: str = Form(...),
    title: str = Form(...),
    company: str = Form(...),
    link: str = Form(""),
    score: int = Form(0),
    status: str = Form("prepared")
):
    conn = db()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO applications
    (user_id, job_id, title, company, link, score, status, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, job_id, title, company, link, score, status, now(), now()))
    app_id = cur.lastrowid
    conn.commit()
    conn.close()
    add_alert(user_id, f"Application added: {title}")
    return {"ok": True, "app_id": app_id}


@app.get("/api/applications/{user_id}")
def list_applications(user_id: int):
    conn = db()
    rows = conn.execute(
        "SELECT * FROM applications WHERE user_id=? ORDER BY id DESC",
        (user_id,)
    ).fetchall()
    conn.close()
    return {"items": [dict(r) for r in rows]}


@app.post("/api/applications/{user_id}/{app_id}/status")
def update_application_status(user_id: int, app_id: int, status: str = Form(...)):
    conn = db()
    conn.execute(
        "UPDATE applications SET status=?, updated_at=? WHERE id=? AND user_id=?",
        (status, now(), app_id, user_id)
    )
    conn.commit()
    conn.close()
    add_alert(user_id, f"Application status updated to {status}.")
    return {"ok": True}


@app.get("/api/tracking/{user_id}")
def tracking(user_id: int):
    return dashboard(user_id)["tracking"]


@app.post("/api/income/{user_id}")
def add_income(
    user_id: int,
    amount: int = Form(...),
    source: str = Form("Manual"),
    note: str = Form("")
):
    conn = db()
    conn.execute("""
    INSERT INTO income (user_id, amount, source, note, created_at)
    VALUES (?, ?, ?, ?, ?)
    """, (user_id, amount, source, note, now()))
    conn.commit()
    conn.close()
    add_alert(user_id, f"Income added: Rs.{amount}")
    return {"ok": True}


@app.get("/api/income/{user_id}")
def list_income(user_id: int):
    conn = db()
    rows = conn.execute(
        "SELECT * FROM income WHERE user_id=? ORDER BY id DESC",
        (user_id,)
    ).fetchall()
    conn.close()
    return {"items": [dict(r) for r in rows]}


@app.get("/api/apply-engine/plan/{user_id}")
def apply_engine_plan(user_id: int, limit: int = 10, min_score: int = 55):
    job_list = jobs(user_id, min_score=min_score)["jobs"][:limit]
    return {"items": job_list, "count": len(job_list), "min_score": min_score}


@app.get("/api/automation/{user_id}")
def automation(user_id: int, limit: int = 20, min_score: int = 55):
    conn = db()
    apps = conn.execute(
        "SELECT * FROM applications WHERE user_id=?",
        (user_id,)
    ).fetchall()
    conn.close()

    high_jobs = jobs(user_id, min_score=min_score)["jobs"]
    prepared = len([a for a in apps if a["status"] == "prepared"])
    applied_today = len(apps)

    projected_7d = 250 + prepared * 200
    projected_30d = projected_7d * 4 + 50

    return {
        "mode": "Daily Mode ON",
        "recommended_queue_size": len(high_jobs) if high_jobs else limit,
        "high_score_jobs": len(high_jobs),
        "min_score": min_score,
        "commands": [
            f"Prepare {len(high_jobs) if high_jobs else limit} applications from high-fit jobs.",
            "Submit 5 prepared applications today.",
            "Track all submitted applications and update statuses.",
            "Complete 1 microjob or 1 skill-gap task if job scores are weak."
        ],
        "top_jobs": high_jobs[:limit],
        "followups_due": [],
        "forecast": {
            "projected_7d": projected_7d,
            "projected_30d": projected_30d,
            "message": f"Estimated opportunity momentum is Rs.{projected_7d} in 7 days and Rs.{projected_30d} in 30 days."
        },
        "streak": {
            "streak_days": 1 if applied_today else 0,
            "today_applications": applied_today,
            "message": f"{1 if applied_today else 0}-day streak. {applied_today} applications prepared/submitted today."
        },
        "metrics": dashboard(user_id)["tracking"]
    }


@app.post("/api/automation/queue/{user_id}")
def automation_queue(
    user_id: int,
    limit: int = Form(10),
    min_score: int = Form(55)
):
    top = jobs(user_id, min_score=min_score)["jobs"][:limit]
    prepared = []
    skipped = []

    conn = db()
    cur = conn.cursor()

    for j in top:
        exists = cur.execute(
            "SELECT id FROM applications WHERE user_id=? AND job_id=?",
            (user_id, j["id"])
        ).fetchone()

        if exists:
            skipped.append(j["id"])
            continue

        cur.execute("""
        INSERT INTO applications
        (user_id, job_id, title, company, link, score, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, 'prepared', ?, ?)
        """, (user_id, j["id"], j["title"], j["company"], j["apply_url"], j["match_score"], now(), now()))

        prepared.append(j["id"])

    conn.commit()
    conn.close()

    add_alert(user_id, f"Automation prepared {len(prepared)} applications. Skipped {len(skipped)} duplicates.")
    return {"ok": True, "prepared": prepared, "skipped": skipped, "count": len(prepared)}


@app.get("/api/automation/followups/{user_id}")
def automation_followups(user_id: int):
    conn = db()
    rows = conn.execute("""
    SELECT * FROM applications
    WHERE user_id=? AND status IN ('applied','viewed')
    ORDER BY updated_at ASC
    """, (user_id,)).fetchall()
    conn.close()
    return {"items": [dict(r) for r in rows]}


@app.get("/api/automation/followup-message/{user_id}/{app_id}")
def followup_message(user_id: int, app_id: int):
    conn = db()
    app_row = conn.execute(
        "SELECT * FROM applications WHERE id=? AND user_id=?",
        (app_id, user_id)
    ).fetchone()
    conn.close()

    if not app_row:
        raise HTTPException(status_code=404, detail="Application not found")

    return {
        "message": f"""Hi {app_row['company']} team,

I wanted to follow up on my application for the {app_row['title']} role.

I remain interested and would be glad to contribute with structured, reliable, and outcome-focused work.

Best regards"""
    }


@app.post("/api/automation/followup-sent/{user_id}/{app_id}")
def followup_sent(user_id: int, app_id: int):
    add_alert(user_id, f"Follow-up marked as sent for application {app_id}.")
    return {"ok": True}


@app.get("/api/automation/forecast/{user_id}")
def automation_forecast(user_id: int):
    return automation(user_id)["forecast"]


@app.get("/api/subscription/{user_id}")
def subscription(user_id: int):
    user = user_profile(user_id)
    return {
        "user_id": user_id,
        "plan": user.get("plan", "free"),
        "pro_until": user.get("pro_until", "")
    }


@app.post("/api/payments/create-order/{user_id}")
def create_payment_order(user_id: int):
    if not RAZORPAY_KEY or not RAZORPAY_SECRET:
        raise HTTPException(status_code=500, detail="Razorpay keys missing")

    if razorpay is None:
        raise HTTPException(status_code=500, detail="Razorpay package not installed")

    amount_paise = PRO_PRICE_INR * 100
    client = razorpay.Client(auth=(RAZORPAY_KEY, RAZORPAY_SECRET))

    order = client.order.create({
        "amount": amount_paise,
        "currency": "INR",
        "payment_capture": 1,
        "notes": {"user_id": str(user_id), "plan": "pro"}
    })

    conn = db()
    conn.execute("""
    INSERT INTO payments (user_id, razorpay_order_id, amount, currency, status, created_at)
    VALUES (?, ?, ?, 'INR', 'created', ?)
    """, (user_id, order["id"], amount_paise, now()))
    conn.commit()
    conn.close()

    return {
        "key_id": RAZORPAY_KEY,
        "order_id": order["id"],
        "amount": amount_paise,
        "currency": "INR",
        "plan": "pro"
    }


@app.post("/api/payments/verify/{user_id}")
def verify_payment(user_id: int, payload: dict = Body(...)):
    order_id = payload.get("razorpay_order_id")
    payment_id = payload.get("razorpay_payment_id")
    signature = payload.get("razorpay_signature")

    if not order_id or not payment_id or not signature:
        raise HTTPException(status_code=400, detail="Missing payment verification fields")

    generated = hmac.new(
        RAZORPAY_SECRET.encode(),
        f"{order_id}|{payment_id}".encode(),
        hashlib.sha256
    ).hexdigest()

    if generated != signature:
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    pro_until = (datetime.now() + timedelta(days=30)).isoformat(timespec="seconds")

    conn = db()
    conn.execute("""
    UPDATE users
    SET plan='pro', pro_until=?, razorpay_payment_id=?, razorpay_order_id=?
    WHERE id=?
    """, (pro_until, payment_id, order_id, user_id))

    conn.execute("""
    UPDATE payments
    SET razorpay_payment_id=?, status='paid'
    WHERE user_id=? AND razorpay_order_id=?
    """, (payment_id, user_id, order_id))

    conn.commit()
    conn.close()

    add_alert(user_id, "Payment successful. Pro plan unlocked.")

    return {
        "ok": True,
        "message": "Pro unlocked",
        "plan": "pro",
        "pro_until": pro_until
    }