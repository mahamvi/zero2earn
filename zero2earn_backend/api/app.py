import os
import json
import threading
import time
from fastapi import FastAPI, Form, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from datetime import datetime, timedelta
import sqlite3
import hashlib
import os
import re
import random
import json
import hmac
import razorpay
import requests
from dotenv import load_dotenv
try:
    from groq import Groq
except Exception:
    Groq = None

load_dotenv()

app = FastAPI(title="Zero2Earn AI SaaS", version="5.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = Path(os.getenv("DATABASE_PATH", BASE_DIR / "zero2earn.db"))


def now():
    return datetime.now().isoformat(timespec="seconds")


def db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def rows_to_dicts(rows):
    return [dict(r) for r in rows]


def hash_password(password: str):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def check_password(input_password: str, stored_password: str):
    return stored_password in [input_password, hash_password(input_password)]


def add_column(cur, table, column, definition):
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
        location TEXT DEFAULT 'India',
        experience_years INTEGER DEFAULT 0,
        track TEXT DEFAULT 'Universal',
        stage TEXT DEFAULT 'Starter',
        goal_daily INTEGER DEFAULT 500,
        plan TEXT DEFAULT 'free',
        pro_until TEXT DEFAULT '',
        recruiter_visible INTEGER DEFAULT 1,
        created_at TEXT DEFAULT ''
    )
    """)

    for col, definition in {
        "headline": "TEXT DEFAULT ''",
        "summary": "TEXT DEFAULT ''",
        "skills": "TEXT DEFAULT ''",
        "resume_text": "TEXT DEFAULT ''",
        "location": "TEXT DEFAULT 'India'",
        "experience_years": "INTEGER DEFAULT 0",
        "track": "TEXT DEFAULT 'Universal'",
        "stage": "TEXT DEFAULT 'Starter'",
        "goal_daily": "INTEGER DEFAULT 500",
        "plan": "TEXT DEFAULT 'free'",
        "pro_until": "TEXT DEFAULT ''",
        "recruiter_visible": "INTEGER DEFAULT 1",
        "created_at": "TEXT DEFAULT ''",
        "streak_days": "INTEGER DEFAULT 0",
        "last_active_date": "TEXT DEFAULT ''",
        "total_tasks_completed": "INTEGER DEFAULT 0",
    }.items():
        add_column(cur, "users", col, definition)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        description TEXT,
        estimated_reward INTEGER DEFAULT 0,
        status TEXT DEFAULT 'pending',
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
        url TEXT,
        score INTEGER DEFAULT 0,
        status TEXT DEFAULT 'saved',
        proposal TEXT DEFAULT '',
        cover_letter TEXT DEFAULT '',
        follow_up TEXT DEFAULT '',
        created_at TEXT DEFAULT ''
    )
    """)


    cur.execute("""
    CREATE TABLE IF NOT EXISTS followups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        application_id INTEGER,
        title TEXT DEFAULT '',
        company TEXT DEFAULT '',
        due_date TEXT DEFAULT '',
        message TEXT DEFAULT '',
        status TEXT DEFAULT 'pending',
        created_at TEXT DEFAULT ''
    )
    """)


    for col, definition in {
        "applied_at": "TEXT DEFAULT ''",
        "follow_up_due": "TEXT DEFAULT ''",
        "reply_note": "TEXT DEFAULT ''",
        "income_value": "INTEGER DEFAULT 0",
        "apply_source": "TEXT DEFAULT ''"
    }.items():
        add_column(cur, "applications", col, definition)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS income (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        source TEXT,
        amount INTEGER DEFAULT 0,
        note TEXT DEFAULT '',
        created_at TEXT DEFAULT ''
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS shortlists (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recruiter_name TEXT,
        recruiter_email TEXT,
        company TEXT,
        user_id INTEGER,
        status TEXT DEFAULT 'shortlisted',
        note TEXT DEFAULT '',
        created_at TEXT DEFAULT ''
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS contact_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recruiter_name TEXT,
        recruiter_email TEXT,
        company TEXT,
        user_id INTEGER,
        role TEXT DEFAULT '',
        message TEXT DEFAULT '',
        status TEXT DEFAULT 'new',
        created_at TEXT DEFAULT ''
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS recruiter_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recruiter_name TEXT,
        recruiter_email TEXT,
        company TEXT,
        title TEXT,
        description TEXT DEFAULT '',
        required_skills TEXT DEFAULT '',
        location TEXT DEFAULT 'India / Remote',
        salary_range TEXT DEFAULT '',
        job_type TEXT DEFAULT 'Full-time / Contract',
        status TEXT DEFAULT 'open',
        created_at TEXT DEFAULT ''
    )
    """)


    cur.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        razorpay_order_id TEXT DEFAULT '',
        razorpay_payment_id TEXT DEFAULT '',
        razorpay_signature TEXT DEFAULT '',
        amount INTEGER DEFAULT 0,
        currency TEXT DEFAULT 'INR',
        status TEXT DEFAULT 'created',
        plan TEXT DEFAULT 'pro',
        created_at TEXT DEFAULT '',
        verified_at TEXT DEFAULT ''
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS ai_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        feature TEXT DEFAULT 'wingman',
        created_at TEXT DEFAULT ''
    )
    """)

    cur.execute("""
    INSERT OR IGNORE INTO users
    (id, name, email, password, headline, summary, skills, resume_text, location, experience_years, track, stage, goal_daily, plan, recruiter_visible, created_at)
    VALUES
    (1, 'Dr Ramesh', 'demo@zero2earn.ai', ?,
    'MBBS Doctor | General Physician | Diabetologist | AI Medical Writer | Healthcare Consultant',
    'Doctor with 11+ years of clinical practice, emergency care, healthcare consulting, medical writing, AI-assisted workflows, remote work readiness, and consulting capability.',
    'medical writing, healthcare consulting, diabetes care, general medicine, emergency care, telemedicine, clinical research, patient education, AI tools, content writing',
    'MBBS doctor with 11+ years experience in clinical practice, emergency care, diabetes management, healthcare consulting, medical writing, patient education and AI-assisted healthcare workflows.',
    'Warangal, Telangana, India',
    11,
    'Expert', 'Premium', 500, 'pro', 1, ?)
    """, (hash_password("demo123"), now()))

    conn.commit()
    conn.close()


init_db()


def get_user(user_id: int):
    conn = db()
    row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return dict(row)


def extract_resume_skills(text: str):
    bank = [
        "medical writing", "healthcare consulting", "clinical research", "telemedicine",
        "patient education", "diabetes care", "general medicine", "emergency care",
        "ai tools", "content writing", "data entry", "research", "documentation",
        "freelance writing", "medical review", "healthcare operations", "remote work",
        "proposal writing", "communication", "case studies", "AI evaluation",
        "patient support", "claims review", "medical documentation"
    ]
    low = (text or "").lower()
    found = [s for s in bank if s in low]
    if not found:
        found = ["medical writing", "healthcare consulting", "AI tools", "research"]
    return found[:14]


def split_skills(skills_text):
    return [s.strip() for s in (skills_text or "").split(",") if s.strip()]


def extract_keywords(user):
    text = " ".join([
        user.get("headline", ""),
        user.get("summary", ""),
        user.get("skills", ""),
        user.get("resume_text", "")
    ]).lower()

    preferred = [
        "medical writing", "healthcare consultant", "clinical research",
        "telemedicine", "doctor", "diabetes care", "patient education",
        "AI healthcare", "medical content", "healthcare operations",
        "content writing", "remote assistant", "data entry", "freelance writing",
        "AI evaluation", "medical reviewer", "patient support"
    ]

    found = []
    for kw in preferred:
        if any(part.lower() in text for part in kw.split()):
            found.append(kw)

    words = re.findall(r"[a-zA-Z]{5,}", text)
    for w in words:
        if len(found) >= 14:
            break
        if w not in found and w not in ["doctor", "ready", "using", "years"]:
            found.append(w)

    if not found:
        found = ["medical writing", "content writing", "data entry", "virtual assistant"]

    return list(dict.fromkeys(found))[:14]


def make_url(template, keyword):
    q = keyword.replace(" ", "+")
    dash = keyword.replace(" ", "-")
    return template.replace("{q}", q).replace("{dash}", dash)


INDIA_PORTALS = [
    ("LinkedIn India", "https://www.linkedin.com/jobs/search/?keywords={q}&location=India"),
    ("Indeed India", "https://in.indeed.com/jobs?q={q}&l=India"),
    ("Naukri", "https://www.naukri.com/{dash}-jobs"),
    ("Foundit", "https://www.foundit.in/srp/results?query={q}"),
    ("TimesJobs", "https://www.timesjobs.com/candidate/job-search.html?searchType=personalizedSearch&txtKeywords={q}&txtLocation=India"),
    ("Internshala", "https://internshala.com/jobs/{dash}-jobs"),
    ("Apna", "https://apna.co/jobs?search=true&text={q}"),
    ("Instahyre", "https://www.instahyre.com/search-jobs/?skills={q}")
]

GLOBAL_PORTALS = [
    ("RemoteOK", "https://remoteok.com/remote-{dash}-jobs"),
    ("Remotive", "https://remotive.com/remote-jobs/search?search={q}"),
    ("We Work Remotely", "https://weworkremotely.com/remote-jobs/search?term={q}"),
    ("Upwork", "https://www.upwork.com/search/jobs/?q={q}"),
    ("Fiverr", "https://www.fiverr.com/search/gigs?query={q}"),
    ("Freelancer", "https://www.freelancer.com/jobs/?keyword={q}"),
    ("PeoplePerHour", "https://www.peopleperhour.com/freelance-jobs/{dash}")
]

MICRO_PLATFORMS = [
    ("UserTesting", "https://www.usertesting.com/get-paid-to-test", "Website/app testing", "₹500-₹3,000/test"),
    ("uTest", "https://www.utest.com/tester-signup", "Software testing", "Project based"),
    ("Clickworker", "https://www.clickworker.com/clickworker/", "Micro tasks + UHRS", "₹200-₹3,000/day"),
    ("Toloka", "https://toloka.ai/tolokers", "AI/data tasks", "₹200-₹2,000/day"),
    ("OneForma", "https://www.oneforma.com/jobs/", "AI data projects", "Project based"),
    ("Appen", "https://appen.com/jobs/", "AI training projects", "Project based"),
    ("DataAnnotation", "https://www.dataannotation.tech/", "AI evaluation", "Skill based"),
    ("Outlier AI", "https://outlier.ai/", "AI expert tasks", "Skill based"),
    ("Respondent", "https://www.respondent.io/respondents", "Paid research", "High payout"),
    ("TestingTime", "https://www.testingtime.com/en/become-a-paid-testuser/", "User interviews", "Per study")
]


def build_job_cards(user):
    keywords = extract_keywords(user)
    jobs = []
    idx = 1

    title_bank = [
        "Medical Writer", "Healthcare Content Reviewer", "Clinical Research Assistant",
        "AI Medical Evaluator", "Telemedicine Consultant", "Patient Education Writer",
        "Healthcare Virtual Assistant", "Medical Documentation Specialist",
        "Medical Claims Reviewer", "Healthcare Operations Associate"
    ]

    for kw in keywords:
        for portal, template in INDIA_PORTALS:
            score = random.randint(70, 96)
            title = random.choice(title_bank) if any(x in kw.lower() for x in ["medical", "health", "clinical", "doctor", "patient"]) else f"{kw.title()} Specialist"
            jobs.append({
                "id": f"ind-{idx}",
                "title": title,
                "company": portal,
                "location": "India / Remote / Hybrid",
                "category": "India-first job",
                "source": portal,
                "score": score,
                "win_chance": min(96, score + random.randint(-4, 5)),
                "url": make_url(template, kw),
                "expected_earning": "₹15,000-₹80,000/month",
                "difficulty": "Medium",
                "payout_speed": "Monthly / project-based",
                "description": f"Search-ready opportunity for {kw}. Open official portal and apply to active listings.",
                "match_reason": [f"Matches keyword: {kw}", "India-first source", "Suitable for resume-based application"],
                "proposal": f"Hello, I am interested in this {title} opportunity. I bring healthcare experience, reliable communication, domain knowledge, and AI-assisted productivity. I can support this role with accuracy, discipline, and fast execution.",
                "cover_letter": f"Dear Hiring Manager,\n\nI am applying for the {title} role. My background in healthcare, clinical work, medical writing, and AI-assisted workflows makes me a strong fit. I can contribute with accuracy, responsibility, and practical domain knowledge.\n\nRegards,\nDr Ramesh",
                "safety_note": "Apply only through official portal. Never pay to apply."
            })
            idx += 1

    for kw in keywords:
        for portal, template in GLOBAL_PORTALS:
            score = random.randint(58, 90)
            jobs.append({
                "id": f"glob-{idx}",
                "title": f"Remote {kw.title()} Work",
                "company": portal,
                "location": "Global Remote",
                "category": "Global remote / freelance",
                "source": portal,
                "score": score,
                "win_chance": min(92, score + random.randint(-5, 6)),
                "url": make_url(template, kw),
                "expected_earning": "₹5,000-₹1,50,000/month",
                "difficulty": "Medium",
                "payout_speed": "Weekly / milestone / monthly",
                "description": f"Remote/global opportunity search for {kw}.",
                "match_reason": [f"Matches keyword: {kw}", "Remote-friendly path", "Good for freelance or global applications"],
                "proposal": f"Hi, I can help with {kw} work using my healthcare knowledge, writing skills, research ability, and AI-assisted workflow. I focus on accuracy, clarity, and timely delivery.",
                "cover_letter": f"Dear Hiring Team,\n\nI am interested in remote {kw} opportunities. I have a healthcare background and can support writing, review, research, documentation, and AI-assisted content tasks with professional quality.\n\nRegards,\nDr Ramesh",
                "safety_note": "Use platform protection or escrow where possible. Avoid upfront payment work."
            })
            idx += 1

    return sorted(jobs, key=lambda x: x["score"], reverse=True)[:140]


def calculate_resume_score(user):
    resume_text = user.get("resume_text") or ""
    skills = split_skills(user.get("skills"))
    score = 30
    if resume_text:
        score += min(30, len(resume_text) // 120)
    if user.get("headline"):
        score += 10
    if user.get("summary"):
        score += 10
    score += min(20, len(skills) * 2)
    return max(35, min(100, score))


def calculate_activity_score(user_id):
    conn = db()
    try:
        app_count = conn.execute("SELECT COUNT(*) c FROM applications WHERE user_id=?", (user_id,)).fetchone()["c"]
        task_done = conn.execute("SELECT COUNT(*) c FROM tasks WHERE user_id=? AND status='completed'", (user_id,)).fetchone()["c"]
        income_count = conn.execute("SELECT COUNT(*) c FROM income WHERE user_id=?", (user_id,)).fetchone()["c"]

        # Streak columns may not exist in older databases, so keep this safe.
        streak = 0
        total_done = task_done
        try:
            user_row = conn.execute("SELECT streak_days, total_tasks_completed FROM users WHERE id=?", (user_id,)).fetchone()
            if user_row:
                streak = int(user_row["streak_days"] or 0)
                total_done = int(user_row["total_tasks_completed"] or task_done)
        except Exception:
            streak = 0
            total_done = task_done

        return min(100, app_count * 5 + task_done * 12 + income_count * 15 + streak * 4 + total_done * 3 + 20)
    finally:
        conn.close()


def calculate_income_proof(user_id):
    conn = db()
    row = conn.execute("SELECT COALESCE(SUM(amount),0) total FROM income WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return int(row["total"] or 0)


def calculate_application_score(user_id):
    conn = db()
    app_count = conn.execute("SELECT COUNT(*) c FROM applications WHERE user_id=?", (user_id,)).fetchone()["c"]
    high_score = conn.execute("SELECT COUNT(*) c FROM applications WHERE user_id=? AND score>=70", (user_id,)).fetchone()["c"]
    conn.close()
    return min(100, app_count * 6 + high_score * 4)


def calculate_skill_score(user):
    skills = split_skills(user.get("skills"))
    score = min(100, len(skills) * 9)
    high_value = ["medical writing", "healthcare consulting", "clinical research", "ai tools", "telemedicine", "content writing", "AI evaluation"]
    for hv in high_value:
        if hv.lower() in (user.get("skills") or "").lower():
            score += 5
    return min(100, max(30, score))


def calculate_talent_profile(user):
    user_id = user["id"]
    resume_score = calculate_resume_score(user)
    activity_score = calculate_activity_score(user_id)
    app_score = calculate_application_score(user_id)
    income_total = calculate_income_proof(user_id)
    income_score = min(100, income_total // 100)
    skill_score = calculate_skill_score(user)

    talent_score = round(
        resume_score * 0.30 +
        activity_score * 0.20 +
        app_score * 0.20 +
        income_score * 0.15 +
        skill_score * 0.15
    )

    level = "Starter"
    if talent_score >= 60:
        level = "Professional"
    if talent_score >= 78 or user.get("plan") in ["pro", "company", "college"]:
        level = "Expert / Premium"

    skills = split_skills(user.get("skills"))
    proof = []
    if resume_score >= 70:
        proof.append("Resume-ready")
    if len(skills) >= 5:
        proof.append("Skill profile built")
    if app_score >= 40:
        proof.append("Active applicant")
    if income_total > 0:
        proof.append("Income proof added")
    if user.get("experience_years", 0) and int(user.get("experience_years") or 0) >= 3:
        proof.append("Experienced professional")

    missing = []
    if resume_score < 70:
        missing.append("Improve resume proof points")
    if len(skills) < 6:
        missing.append("Add more verified skills")
    if app_score < 40:
        missing.append("Prepare/apply to more jobs")
    if income_total <= 0:
        missing.append("Add income or project proof")

    return {
        "id": user["id"],
        "name": user.get("name", ""),
        "email": user.get("email", ""),
        "headline": user.get("headline", ""),
        "summary": user.get("summary", ""),
        "location": user.get("location", "India"),
        "experience_years": int(user.get("experience_years") or 0),
        "skills": skills,
        "plan": user.get("plan", "free"),
        "track": user.get("track", "Universal"),
        "stage": user.get("stage", "Starter"),
        "resume_score": resume_score,
        "activity_score": activity_score,
        "application_score": app_score,
        "income_proof": income_total,
        "skill_score": skill_score,
        "talent_score": talent_score,
        "level": level,
        "ready_for_hire": talent_score >= 55,
        "proof_badges": proof,
        "missing_actions": missing,
        "recruiter_pitch": f"{user.get('name','Candidate')} is positioned for {', '.join(skills[:3]) if skills else 'remote work'} roles with a talent readiness score of {talent_score}."
    }


@app.get("/")
def home():
    return {"app": "Zero2Earn AI", "status": "running", "version": "5.0.0"}


@app.get("/health")
def health():
    return {"status": "ok", "db": str(DB_PATH), "version": "5.0.0"}


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
        (name, email, password, headline, summary, skills, goal_daily, plan, recruiter_visible, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'free', 1, ?)
        """, (
            name.strip() or "New User",
            email.lower().strip(),
            hash_password(password),
            "New Zero2Earn user",
            "Ready to build income through jobs, skills, freelance work, and career growth.",
            "",
            int(goal_daily or 500),
            now()
        ))
        conn.commit()
        user_id = cur.lastrowid
        return {
            "status": "created",
            "user_id": user_id,
            "name": name,
            "email": email.lower().strip(),
            "plan": "free",
            "message": "Account created"
        }
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Email already exists")
    finally:
        conn.close()


@app.post("/api/login")
def login(email: str = Form(...), password: str = Form(...)):
    conn = db()
    row = conn.execute("SELECT * FROM users WHERE email=?", (email.lower().strip(),)).fetchone()
    conn.close()
    if not row or not check_password(password, row["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"user_id": row["id"], "name": row["name"], "email": row["email"], "plan": row["plan"]}


@app.get("/api/dashboard/{user_id}")
def dashboard(user_id: int):
    user = get_user(user_id)
    conn = db()
    apps = conn.execute("SELECT * FROM applications WHERE user_id=?", (user_id,)).fetchall()
    income_rows = conn.execute("SELECT * FROM income WHERE user_id=?", (user_id,)).fetchall()
    tasks = conn.execute("SELECT * FROM tasks WHERE user_id=? ORDER BY id DESC LIMIT 10", (user_id,)).fetchall()

    if not tasks:
        seed = [
            ("Complete Daily Command", "Finish resume, jobs, Wingman, micro-income, and tracker steps.", 500),
            ("Apply to 3 strong jobs", "Use Jobs Engine and Wingman before applying.", 300),
            ("Start 1 backup income platform", "Choose UserTesting, Toloka, Clickworker, OneForma, or uTest.", 200),
            ("Improve profile for recruiters", "Add proof, skills, portfolio, and case examples.", 100)
        ]
        for title, desc, reward in seed:
            conn.execute("INSERT INTO tasks (user_id, title, description, estimated_reward, status, created_at) VALUES (?, ?, ?, ?, 'pending', ?)", (user_id, title, desc, reward, now()))
        conn.commit()
        tasks = conn.execute("SELECT * FROM tasks WHERE user_id=? ORDER BY id DESC LIMIT 10", (user_id,)).fetchall()

    conn.close()

    total_earned = sum(int(r["amount"] or 0) for r in income_rows)
    replies = len([a for a in apps if a["status"] in ["reply", "interview", "hired"]])
    interviews = len([a for a in apps if a["status"] in ["interview", "hired"]])

    return {
        "user": user,
        "metrics": {
            "today_target": user.get("goal_daily", 500) or 500,
            "total_earned": total_earned,
            "jobs_applied": len(apps),
            "replies": replies,
            "interviews": interviews,
            "pending_tasks": len([t for t in tasks if t["status"] != "completed"])
        },
        "talent": calculate_talent_profile(user),
        "tasks": rows_to_dicts(tasks)
    }


@app.get("/api/daily-command/{user_id}")
def daily_command(user_id: int):
    user = get_user(user_id)
    talent = calculate_talent_profile(user)

    return {
        "title": "Daily Command",
        "positioning": "Universal income, career, skill and talent operating system for job seekers, students, professionals, freelancers, colleges, recruiters and companies.",
        "level": talent["level"],
        "today_target": user.get("goal_daily", 500) or 500,
        "talent_score": talent["talent_score"],
        "primary_goal": "Earn today, improve skills, apply smarter, track progress, and become recruiter-ready.",
        "actions": [
            {"step": 1, "title": "Resume Power Check", "route": "resume", "description": "Improve keywords, proof points, ATS readiness and role targeting.", "impact": "Better profile strength"},
            {"step": 2, "title": "Apply to Best-Match Jobs", "route": "jobs", "description": "Use India-first, global remote and freelance opportunities matched to your profile.", "impact": "More relevant applications"},
            {"step": 3, "title": "Use Wingman", "route": "wingman", "description": "Generate proposal, cover letter and follow-up for each job.", "impact": "Better reply chance"},
            {"step": 4, "title": "Build Talent Score", "route": "talent", "description": "Improve recruiter readiness with proof, skills, activity and income evidence.", "impact": "Higher hiring visibility"},
            {"step": 5, "title": "Recruiter Visibility", "route": "recruiter", "description": "Understand how companies see verified talent and shortlists.", "impact": "B2B revenue engine"}
        ],
        "trust_rules": ["Never pay to apply", "Use official portals only", "Track every application", "Follow up after 3–5 days", "Build skills while applying"]
    }


@app.get("/api/jobs/{user_id}")
def jobs(user_id: int):
    return {"items": build_job_cards(get_user(user_id))}


@app.get("/api/micro-jobs/{user_id}")
def micro_jobs(user_id: int):
    items = []
    for name, url, category, earning in MICRO_PLATFORMS:
        items.append({
            "name": name,
            "url": url,
            "category": category,
            "earning_range": earning,
            "why": "Useful backup income source for testing, annotation, AI evaluation, surveys, or short tasks.",
            "payout_speed": "Fast to monthly",
            "difficulty": "Easy-Medium",
            "trust_score": random.randint(70, 94),
            "safety_note": "Use official signup only. Never pay to join."
        })
    return {"items": items}


@app.post("/api/resume/paste/{user_id}")
def paste_resume(user_id: int, text: str = Form(...)):
    skills = extract_resume_skills(text)
    conn = db()
    conn.execute("""
    UPDATE users SET resume_text=?, skills=?, headline=?, summary=? WHERE id=?
    """, (
        text[:30000],
        ", ".join(skills),
        "Resume analyzed: AI job matching and recruiter visibility ready",
        "Resume analyzed for jobs, skills, Wingman proposals, talent scoring and recruiter readiness.",
        user_id
    ))
    conn.commit()
    conn.close()
    return {"status": "saved", "resume_score": min(95, max(45, len(text) // 60)), "skills": skills}


@app.post("/api/resume/upload/{user_id}")
async def upload_resume(user_id: int, file: UploadFile = File(...)):
    raw = await file.read()
    text = raw.decode("utf-8", errors="ignore")
    skills = extract_resume_skills(text)
    conn = db()
    conn.execute("""
    UPDATE users SET resume_text=?, skills=?, headline=?, summary=? WHERE id=?
    """, (
        text[:30000],
        ", ".join(skills),
        "Resume uploaded: AI job matching and recruiter visibility ready",
        "Resume analyzed for jobs, skills, Wingman proposals, talent scoring and recruiter readiness.",
        user_id
    ))
    conn.commit()
    conn.close()
    return {"status": "uploaded", "resume_score": min(95, max(45, len(text) // 60)), "skills": skills}


@app.get("/api/resume/status/{user_id}")
def resume_status(user_id: int):
    user = get_user(user_id)
    has_resume = bool(user.get("resume_text"))
    return {
        "uploaded": has_resume,
        "resume_score": calculate_resume_score(user),
        "headline": user.get("headline", ""),
        "summary": user.get("summary", ""),
        "skills": split_skills(user.get("skills")),
        "missing_keywords": ["portfolio", "results", "remote collaboration", "case studies", "tools"]
    }


@app.post("/api/resume/optimize/{user_id}")
def optimize_resume(user_id: int):
    user = get_user(user_id)
    return {
        "resume_score": 88,
        "optimized_headline": "Healthcare Professional | AI Medical Writer | Remote Healthcare Consultant | Clinical Content Specialist",
        "optimized_summary": "Healthcare professional with clinical experience, medical writing ability, AI-assisted productivity and consulting mindset, positioned for remote healthcare, content, research and expert evaluation roles.",
        "skills": extract_keywords(user),
        "recommended_bullets": [
            "Created patient education and healthcare content using clinical knowledge.",
            "Managed OPD/IPD cases and supported emergency decision-making.",
            "Used AI tools to improve writing, research and workflow speed.",
            "Prepared for remote roles in healthcare writing, consulting and AI evaluation."
        ]
    }


@app.post("/api/wingman/{user_id}")
def wingman(user_id: int, title: str = Form(""), company: str = Form(""), url: str = Form(""), category: str = Form(""), description: str = Form("")):
    user = get_user(user_id)
    keywords = extract_keywords(user)
    text = f"{title} {company} {category} {description}".lower()
    score = 50
    reasons = []
    for kw in keywords:
        if kw.lower() in text:
            score += 7
            reasons.append(f"Matches keyword: {kw}")
    score = min(95, score)
    decision = "APPLY" if score >= 65 else "REVIEW BEFORE APPLYING"

    proposal = f"""Hello,

I am interested in the {title or 'role'} at {company or 'your organization'}.

I bring healthcare experience, research ability, medical writing skills, and AI-assisted productivity. I can support this work with accuracy, professionalism, and timely execution.

Regards,
Dr Ramesh"""

    cover_letter = f"""Dear Hiring Manager,

I am applying for the {title or 'available'} role. My background as a healthcare professional and AI-assisted medical writer gives me strong domain knowledge and the ability to deliver clear, accurate, practical work.

I would be glad to contribute to {company or 'your team'}.

Regards,
Dr Ramesh"""

    return {
        "apply_decision": decision,
        "match": {"score": score, "reasons": reasons or ["Relevant but needs manual review."]},
        "proposal": proposal,
        "cover_letter": cover_letter,
        "follow_up": f"Hello, I wanted to follow up on my application for {title or 'the role'}. I remain interested and available to discuss.",
        "checklist": ["Verify company", "Customize first two lines", "Attach resume", "Track application", "Follow up after 3–5 days"]
    }



def ensure_application_columns(conn):
    cur = conn.cursor()
    cols = [r[1] for r in cur.execute("PRAGMA table_info(applications)").fetchall()]

    required = {
        "user_id": "INTEGER DEFAULT 0",
        "job_id": "TEXT DEFAULT ''",
        "title": "TEXT DEFAULT ''",
        "company": "TEXT DEFAULT ''",
        "url": "TEXT DEFAULT ''",
        "score": "INTEGER DEFAULT 0",
        "status": "TEXT DEFAULT 'saved'",
        "proposal": "TEXT DEFAULT ''",
        "cover_letter": "TEXT DEFAULT ''",
        "follow_up": "TEXT DEFAULT ''",
        "created_at": "TEXT DEFAULT ''",
        "applied_at": "TEXT DEFAULT ''",
        "follow_up_due": "TEXT DEFAULT ''",
        "reply_note": "TEXT DEFAULT ''",
        "income_value": "INTEGER DEFAULT 0",
        "apply_source": "TEXT DEFAULT ''"
    }

    for col, definition in required.items():
        if col not in cols:
            cur.execute(f"ALTER TABLE applications ADD COLUMN {col} {definition}")

    conn.commit()


@app.post("/api/wingman/save-application/{user_id}")
def save_application(
    user_id: int,
    job_id: str = Form(""),
    title: str = Form(""),
    company: str = Form(""),
    url: str = Form(""),
    score: int = Form(0),
    proposal: str = Form(""),
    cover_letter: str = Form("")
):
    get_user(user_id)
    conn = db()
    try:
        ensure_application_columns(conn)
        follow_text = f"Hello, I wanted to follow up on my application for {title or 'the role'}."
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO applications
        (user_id, job_id, title, company, url, score, status, proposal, cover_letter, follow_up, apply_source, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 'saved', ?, ?, ?, ?, ?)
        """, (
            user_id,
            job_id or "",
            title or "Untitled role",
            company or "Unknown company",
            url or "#",
            int(score or 0),
            proposal or "",
            cover_letter or "",
            follow_text,
            company or "",
            now()
        ))
        conn.commit()
        application_id = cur.lastrowid
        return {"status": "saved", "application_id": application_id, "message": "Saved to tracker"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Save tracker failed: {str(e)}")
    finally:
        conn.close()



@app.get("/api/automation/{user_id}")
def automation(user_id: int):
    user = get_user(user_id)
    target = int(user.get("goal_daily", 500) or 500)
    return {
        "mode": "Daily Mode ON",
        "queue_target": 20,
        "min_score": 65,
        "commands": [
            "Complete Daily Command",
            "Apply to 3 India-first jobs",
            "Apply to 2 global/freelance jobs",
            "Start or continue 1 micro-income platform",
            "Send 2 follow-ups",
            "Improve one talent score factor"
        ],
        "forecast": {"seven_day": target * 7, "thirty_day": target * 30, "streak_days": 1}
    }


@app.post("/api/automation/queue/{user_id}")
def prepare_queue(user_id: int, min_score: int = Form(65), limit: int = Form(20)):
    jobs = [j for j in build_job_cards(get_user(user_id)) if j["score"] >= min_score][:limit]
    conn = db()
    for job in jobs:
        conn.execute("""
        INSERT INTO applications
        (user_id, job_id, title, company, url, score, status, proposal, cover_letter, follow_up, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 'prepared', ?, ?, ?, ?)
        """, (user_id, job["id"], job["title"], job["company"], job["url"], job["score"], job["proposal"], job["cover_letter"], f"Hello, I wanted to follow up on my application for {job['title']}.", now()))
    conn.commit()
    conn.close()
    return {"prepared": len(jobs), "items": jobs}


@app.get("/api/tracking/{user_id}")
def tracking(user_id: int):
    conn = db()
    rows = conn.execute("SELECT * FROM applications WHERE user_id=? ORDER BY id DESC", (user_id,)).fetchall()
    conn.close()
    return {"items": rows_to_dicts(rows)}


@app.get("/api/income/{user_id}")
def income(user_id: int):
    conn = db()
    rows = conn.execute("SELECT * FROM income WHERE user_id=? ORDER BY id DESC", (user_id,)).fetchall()
    conn.close()
    return {"items": rows_to_dicts(rows)}


@app.post("/api/income/{user_id}")
def add_income(user_id: int, source: str = Form(...), amount: int = Form(...), note: str = Form("")):
    conn = db()
    conn.execute("INSERT INTO income (user_id, source, amount, note, created_at) VALUES (?, ?, ?, ?, ?)", (user_id, source, amount, note, now()))
    conn.commit()
    conn.close()
    return {"status": "saved"}


@app.get("/api/skills/{user_id}")
def skills(user_id: int):
    user = get_user(user_id)
    return {
        "current_skills": extract_keywords(user),
        "missing_skills": ["portfolio", "proposal writing", "remote communication", "case studies", "proof of work"],
        "seven_day_plan": [
            {"day": 1, "skill": "Resume proof points", "task": "Add measurable results and strongest role keywords."},
            {"day": 2, "skill": "Proposal writing", "task": "Create 3 job-specific proposals."},
            {"day": 3, "skill": "Portfolio", "task": "Create 2 sample work pieces."},
            {"day": 4, "skill": "Remote work", "task": "Optimize LinkedIn, Upwork and freelance profiles."},
            {"day": 5, "skill": "Follow-up", "task": "Send polite follow-up messages."},
            {"day": 6, "skill": "Micro income", "task": "Complete onboarding on 2 platforms."},
            {"day": 7, "skill": "Recruiter readiness", "task": "Finalize profile for premium visibility."}
        ]
    }


@app.get("/api/talent-profile/{user_id}")
def talent_profile(user_id: int):
    return calculate_talent_profile(get_user(user_id))


@app.get("/api/talent-pool")
def talent_pool(skill: str = "", location: str = "", min_score: int = 0, ready_only: int = 0):
    conn = db()
    users = rows_to_dicts(conn.execute("SELECT * FROM users WHERE recruiter_visible=1").fetchall())
    conn.close()

    profiles = [calculate_talent_profile(u) for u in users]
    if skill:
        s = skill.lower()
        profiles = [p for p in profiles if s in " ".join(p["skills"]).lower() or s in p["headline"].lower()]
    if location:
        loc = location.lower()
        profiles = [p for p in profiles if loc in (p.get("location") or "").lower()]
    if min_score:
        profiles = [p for p in profiles if p["talent_score"] >= int(min_score)]
    if ready_only:
        profiles = [p for p in profiles if p["ready_for_hire"]]

    profiles = sorted(profiles, key=lambda x: x["talent_score"], reverse=True)
    return {
        "count": len(profiles),
        "items": profiles,
        "business_model": "Companies and colleges can pay for verified talent access, skill reports, placement readiness and hiring shortlists."
    }


@app.get("/api/recruiter/dashboard")
def recruiter_dashboard():
    pool = talent_pool(ready_only=0)["items"]
    short_ready = [p for p in pool if p["ready_for_hire"]]
    expert = [p for p in pool if p["talent_score"] >= 78]
    return {
        "metrics": {
            "total_candidates": len(pool),
            "hire_ready": len(short_ready),
            "expert_candidates": len(expert),
            "average_score": round(sum(p["talent_score"] for p in pool) / max(1, len(pool)))
        },
        "recommended_shortlist": pool[:10],
        "recruiter_value": [
            "Verified activity and readiness score",
            "Skill-matched candidate discovery",
            "Shortlist and contact request pipeline",
            "College/company talent reports",
            "Premium monetization layer for Zero2Earn"
        ]
    }


@app.post("/api/recruiter/shortlist")
def recruiter_shortlist(recruiter_name: str = Form(...), recruiter_email: str = Form(...), company: str = Form(...), user_id: int = Form(...), note: str = Form("")):
    get_user(user_id)
    conn = db()
    conn.execute("""
    INSERT INTO shortlists (recruiter_name, recruiter_email, company, user_id, status, note, created_at)
    VALUES (?, ?, ?, ?, 'shortlisted', ?, ?)
    """, (recruiter_name, recruiter_email, company, user_id, note, now()))
    conn.commit()
    conn.close()
    return {"status": "shortlisted", "candidate_id": user_id}


@app.post("/api/recruiter/contact-request")
def recruiter_contact_request(recruiter_name: str = Form(...), recruiter_email: str = Form(...), company: str = Form(...), user_id: int = Form(...), role: str = Form(""), message: str = Form("")):
    get_user(user_id)
    conn = db()
    conn.execute("""
    INSERT INTO contact_requests (recruiter_name, recruiter_email, company, user_id, role, message, status, created_at)
    VALUES (?, ?, ?, ?, ?, ?, 'new', ?)
    """, (recruiter_name, recruiter_email, company, user_id, role, message, now()))
    conn.commit()
    conn.close()
    return {"status": "contact_request_created", "candidate_id": user_id}


@app.get("/api/recruiter/shortlists")
def recruiter_shortlists():
    conn = db()
    rows = rows_to_dicts(conn.execute("""
    SELECT s.*, u.name, u.headline, u.skills, u.location
    FROM shortlists s
    LEFT JOIN users u ON u.id=s.user_id
    ORDER BY s.id DESC
    """).fetchall())
    conn.close()
    return {"items": rows}


@app.get("/api/recruiter/contact-requests")
def recruiter_contact_requests():
    conn = db()
    rows = rows_to_dicts(conn.execute("""
    SELECT c.*, u.name, u.headline, u.skills, u.location
    FROM contact_requests c
    LEFT JOIN users u ON u.id=c.user_id
    ORDER BY c.id DESC
    """).fetchall())
    conn.close()
    return {"items": rows}


@app.get("/api/plans")
def plans():
    return {
        "items": [
            {"name": "Free", "price": "₹0", "for": "Starters", "features": ["Daily Command", "Basic jobs", "Basic Wingman", "Micro-income links", "Basic talent score"]},
            {"name": "Pro", "price": "₹499/month", "for": "Professionals", "features": ["Premium jobs queue", "Advanced Wingman", "Tracker", "Follow-up engine", "Recruiter visibility boost"]},
            {"name": "College", "price": "Institutional", "for": "Colleges", "features": ["Student readiness dashboard", "Placement workflows", "Skill plans", "Talent reports", "College placement pipeline"]},
            {"name": "Company", "price": "₹4,999/month+", "for": "Recruiters and employers", "features": ["Verified talent pool", "Skill-matched candidates", "Shortlists", "Contact requests", "Hiring pipeline"]}
        ]
    }


@app.post("/api/profile/{user_id}")
def update_profile(user_id: int, name: str = Form(""), headline: str = Form(""), summary: str = Form(""), skills: str = Form(""), location: str = Form(""), experience_years: int = Form(0), goal_daily: int = Form(500), recruiter_visible: int = Form(1)):
    conn = db()
    conn.execute("""
    UPDATE users SET
    name=COALESCE(NULLIF(?, ''), name),
    headline=COALESCE(NULLIF(?, ''), headline),
    summary=COALESCE(NULLIF(?, ''), summary),
    skills=COALESCE(NULLIF(?, ''), skills),
    location=COALESCE(NULLIF(?, ''), location),
    experience_years=?,
    goal_daily=?,
    recruiter_visible=?
    WHERE id=?
    """, (name, headline, summary, skills, location, experience_years, goal_daily, recruiter_visible, user_id))
    conn.commit()
    conn.close()
    return {"status": "updated", "user": get_user(user_id)}


def parse_required_skills(text: str):
    raw = re.split(r"[,;\n|]+", text or "")
    skills = [x.strip().lower() for x in raw if x.strip()]
    if not skills and text:
        skills = re.findall(r"[a-zA-Z][a-zA-Z +#.-]{2,}", text.lower())
    return list(dict.fromkeys(skills))[:20]


def candidate_job_match(candidate, job):
    required = parse_required_skills(job.get("required_skills", ""))
    candidate_skills = [s.lower() for s in candidate.get("skills", [])]
    candidate_text = " ".join([
        candidate.get("headline", ""),
        candidate.get("summary", ""),
        " ".join(candidate.get("skills", [])),
        candidate.get("location", "")
    ]).lower()

    matched = []
    for req in required:
        if req in candidate_text or any(req in cs or cs in req for cs in candidate_skills):
            matched.append(req)

    skill_score = int((len(matched) / max(1, len(required))) * 45)
    talent_score = int(candidate.get("talent_score", 0) * 0.35)
    location_score = 10 if (job.get("location", "").lower() in candidate.get("location", "").lower() or "remote" in job.get("location", "").lower()) else 4
    readiness_score = 10 if candidate.get("ready_for_hire") else 3

    final_score = min(100, skill_score + talent_score + location_score + readiness_score)

    reasons = []
    if matched:
        reasons.append("Matched skills: " + ", ".join(matched[:6]))
    if candidate.get("ready_for_hire"):
        reasons.append("Candidate is hire-ready")
    if candidate.get("talent_score", 0) >= 75:
        reasons.append("Strong talent score")
    if candidate.get("income_proof", 0) > 0:
        reasons.append("Has income/project proof")
    if not reasons:
        reasons.append("Potential candidate, needs manual review")

    return {
        "candidate": candidate,
        "match_score": final_score,
        "matched_skills": matched,
        "match_reasons": reasons,
        "recommended_action": "Contact now" if final_score >= 70 else "Shortlist for review" if final_score >= 50 else "Keep as backup"
    }


@app.get("/api/recruiter/candidate/{user_id}")
def recruiter_candidate_detail(user_id: int):
    user = get_user(user_id)
    talent = calculate_talent_profile(user)

    conn = db()
    apps = rows_to_dicts(conn.execute("SELECT * FROM applications WHERE user_id=? ORDER BY id DESC LIMIT 25", (user_id,)).fetchall())
    incomes = rows_to_dicts(conn.execute("SELECT * FROM income WHERE user_id=? ORDER BY id DESC LIMIT 25", (user_id,)).fetchall())
    contacts = rows_to_dicts(conn.execute("SELECT * FROM contact_requests WHERE user_id=? ORDER BY id DESC LIMIT 10", (user_id,)).fetchall())
    conn.close()

    return {
        "candidate": talent,
        "resume_text": user.get("resume_text", ""),
        "score_breakdown": {
            "resume_score": talent["resume_score"],
            "activity_score": talent["activity_score"],
            "application_score": talent["application_score"],
            "income_score": min(100, talent["income_proof"] // 100),
            "skill_score": talent["skill_score"],
            "final_talent_score": talent["talent_score"]
        },
        "applications": apps,
        "income_proof": incomes,
        "contact_history": contacts,
        "recruiter_summary": {
            "best_for": talent["skills"][:5],
            "risk_flags": talent["missing_actions"],
            "why_shortlist": talent["proof_badges"]
        }
    }


@app.post("/api/recruiter/post-job")
def recruiter_post_job(
    recruiter_name: str = Form(...),
    recruiter_email: str = Form(...),
    company: str = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    required_skills: str = Form(""),
    location: str = Form("India / Remote"),
    salary_range: str = Form(""),
    job_type: str = Form("Full-time / Contract")
):
    conn = db()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO recruiter_jobs
    (recruiter_name, recruiter_email, company, title, description, required_skills, location, salary_range, job_type, status, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?)
    """, (recruiter_name, recruiter_email, company, title, description, required_skills, location, salary_range, job_type, now()))
    conn.commit()
    job_id = cur.lastrowid
    conn.close()

    return {
        "status": "job_posted",
        "job_id": job_id,
        "next_step": f"Open /api/recruiter/job-matches/{job_id} to see matched candidates."
    }


@app.get("/api/recruiter/jobs")
def recruiter_jobs(status: str = "open"):
    conn = db()
    if status == "all":
        rows = rows_to_dicts(conn.execute("SELECT * FROM recruiter_jobs ORDER BY id DESC").fetchall())
    else:
        rows = rows_to_dicts(conn.execute("SELECT * FROM recruiter_jobs WHERE status=? ORDER BY id DESC", (status,)).fetchall())
    conn.close()
    return {"count": len(rows), "items": rows}


@app.get("/api/recruiter/job-matches/{job_id}")
def recruiter_job_matches(job_id: int, limit: int = 15):
    conn = db()
    job = conn.execute("SELECT * FROM recruiter_jobs WHERE id=?", (job_id,)).fetchone()
    conn.close()
    if not job:
        raise HTTPException(status_code=404, detail="Recruiter job not found")

    job = dict(job)
    pool = talent_pool(ready_only=0)["items"]
    matches = [candidate_job_match(c, job) for c in pool]
    matches = sorted(matches, key=lambda x: x["match_score"], reverse=True)[:limit]

    return {
        "job": job,
        "required_skills": parse_required_skills(job.get("required_skills", "")),
        "count": len(matches),
        "matches": matches
    }


@app.post("/api/recruiter/auto-shortlist/{job_id}")
def recruiter_auto_shortlist(
    job_id: int,
    recruiter_name: str = Form("Demo Recruiter"),
    recruiter_email: str = Form("recruiter@company.com"),
    company: str = Form("Demo Company"),
    limit: int = Form(10),
    min_score: int = Form(50)
):
    data = recruiter_job_matches(job_id, limit=50)
    shortlisted = [m for m in data["matches"] if m["match_score"] >= min_score][:limit]

    conn = db()
    for m in shortlisted:
        c = m["candidate"]
        conn.execute("""
        INSERT INTO shortlists (recruiter_name, recruiter_email, company, user_id, status, note, created_at)
        VALUES (?, ?, ?, ?, 'auto_shortlisted', ?, ?)
        """, (
            recruiter_name,
            recruiter_email,
            company,
            c["id"],
            f"Auto-shortlisted for {data['job']['title']} with match score {m['match_score']}%. Reasons: {'; '.join(m['match_reasons'])}",
            now()
        ))
    conn.commit()
    conn.close()

    return {
        "status": "auto_shortlist_complete",
        "job_id": job_id,
        "shortlisted_count": len(shortlisted),
        "items": shortlisted
    }


@app.post("/api/recruiter/job-status/{job_id}")
def recruiter_update_job_status(job_id: int, status: str = Form(...)):
    allowed = ["open", "paused", "closed"]
    if status not in allowed:
        raise HTTPException(status_code=400, detail="Invalid status")
    conn = db()
    conn.execute("UPDATE recruiter_jobs SET status=? WHERE id=?", (status, job_id))
    conn.commit()
    conn.close()
    return {"status": "updated", "job_id": job_id, "new_status": status}


@app.get("/api/score-booster/{user_id}")
def score_booster(user_id: int):
    user = get_user(user_id)
    talent = calculate_talent_profile(user)
    recommended_skills = [
        "medical writing", "AI medical review", "healthcare consulting", "clinical research",
        "patient education", "telemedicine", "AI content evaluation", "medical documentation",
        "healthcare operations", "remote collaboration", "proposal writing", "case study writing"
    ]
    current = [s.lower() for s in split_skills(user.get("skills"))]
    missing_skills = [s for s in recommended_skills if s.lower() not in current]
    actions = []
    if talent["resume_score"] < 70:
        actions.append({"title":"Upgrade resume proof points","impact":"+10 to +20","task":"Add stronger headline, summary, skills, and experience proof."})
    if talent["skill_score"] < 70:
        actions.append({"title":"Add recruiter-ready skills","impact":"+10 to +25","task":"Add medical writing, AI medical review, clinical research, and healthcare consulting keywords."})
    if talent["application_score"] < 40:
        actions.append({"title":"Save/apply to relevant jobs","impact":"+5 to +20","task":"Save 5 strong jobs from Jobs Engine and prepare applications."})
    if talent["income_proof"] <= 0:
        actions.append({"title":"Add proof of work / income proof","impact":"+5 to +15","task":"Add a sample project, writing sample, freelance proof, or practice earning entry."})
    if not actions:
        actions.append({"title":"Profile already strong","impact":"Maintain","task":"Keep applying, tracking, and improving proof."})
    return {
        "current_talent_score": talent["talent_score"],
        "ready_for_hire": talent["ready_for_hire"],
        "current_profile": talent,
        "missing_skills": missing_skills,
        "recommended_skills": recommended_skills,
        "actions": actions,
        "expected_after_boost": min(88, talent["talent_score"] + 35)
    }


@app.post("/api/score-booster/apply/{user_id}")
def apply_score_booster(user_id: int):
    user = get_user(user_id)
    boosted_skills = [
        "medical writing", "AI medical review", "healthcare consulting", "clinical research",
        "patient education", "telemedicine", "AI content evaluation", "medical documentation",
        "healthcare operations", "remote collaboration", "proposal writing", "case study writing",
        "content writing", "research"
    ]
    existing = split_skills(user.get("skills"))
    merged = []
    for s in existing + boosted_skills:
        if s and s.lower() not in [x.lower() for x in merged]:
            merged.append(s)
    resume_text = user.get("resume_text") or ""
    if len(resume_text.strip()) < 300:
        resume_text = """Healthcare professional with clinical experience, healthcare consulting exposure, medical writing ability, patient education experience, clinical research interest, AI-assisted content workflow skills, remote collaboration readiness, and strong domain knowledge for healthcare content, AI medical review, documentation, telemedicine support, and expert evaluation roles.

Experience includes patient care, medical documentation, diabetes care, emergency care, healthcare communication, clinical reasoning, and creation/review of health-related content with accuracy and safety."""
    headline = "Healthcare Professional | AI Medical Reviewer | Medical Writer | Clinical Content Specialist"
    summary = "Healthcare professional positioned for remote healthcare, AI medical review, medical writing, clinical content, patient education, research support, telemedicine and healthcare consulting roles."
    conn = db()
    conn.execute("""
    UPDATE users SET headline=?, summary=?, skills=?, resume_text=?, experience_years=CASE WHEN experience_years < 1 THEN 3 ELSE experience_years END
    WHERE id=?
    """, (headline, summary, ", ".join(merged[:18]), resume_text, user_id))
    booster_tasks = [
        ("Create medical writing sample", "Prepare one 500-word healthcare article or AI medical review sample.", 300),
        ("Save 5 matched jobs", "Use Jobs Engine filters and save five relevant applications.", 300),
        ("Add proof to tracker", "Add project proof, sample work, or income proof in Tracker.", 200),
        ("Prepare recruiter profile", "Review Talent Pool profile and make it hire-ready.", 200)
    ]
    for title, desc, reward in booster_tasks:
        conn.execute("INSERT INTO tasks (user_id, title, description, estimated_reward, status, created_at) VALUES (?, ?, ?, ?, 'pending', ?)", (user_id, title, desc, reward, now()))
    conn.commit()
    conn.close()
    updated = calculate_talent_profile(get_user(user_id))
    return {"status":"boosted","message":"Profile upgraded with recruiter-ready headline, summary, skills, resume proof and score-building tasks.","talent":updated}



@app.get("/api/earning-dashboard/{user_id}")
def earning_dashboard(user_id: int):
    user = get_user(user_id)
    conn = db()
    incomes = rows_to_dicts(conn.execute("SELECT * FROM income WHERE user_id=? ORDER BY id DESC", (user_id,)).fetchall())
    apps = rows_to_dicts(conn.execute("SELECT * FROM applications WHERE user_id=? ORDER BY id DESC", (user_id,)).fetchall())
    tasks = rows_to_dicts(conn.execute("SELECT * FROM tasks WHERE user_id=? ORDER BY id DESC", (user_id,)).fetchall())
    conn.close()

    today = datetime.now().date().isoformat()
    total_income = sum(int(i.get("amount") or 0) for i in incomes)
    today_income = sum(int(i.get("amount") or 0) for i in incomes if str(i.get("created_at","")).startswith(today))
    target = int(user.get("goal_daily", 500) or 500)

    proof_items = []
    for i in incomes[:20]:
        proof_items.append({
            "type": "income",
            "title": i.get("source", "Income proof"),
            "amount": int(i.get("amount") or 0),
            "note": i.get("note", ""),
            "created_at": i.get("created_at", "")
        })

    projected_7 = max(total_income, today_income * 7, target * 7 if today_income >= target else today_income * 7)
    projected_30 = max(total_income, today_income * 30, target * 30 if today_income >= target else today_income * 30)
    completed_tasks = len([t for t in tasks if t.get("status") == "completed"])
    prepared_apps = len([a for a in apps if a.get("status") in ["saved", "prepared", "reply", "interview", "hired"]])
    daily_progress = min(100, round((today_income / max(1, target)) * 100))

    next_actions = []
    if today_income < target:
        next_actions.append("Add one proof item or micro-income activity to move toward today’s target.")
    if prepared_apps < 5:
        next_actions.append("Prepare or save at least 5 strong jobs from Jobs Engine.")
    if completed_tasks < 2:
        next_actions.append("Complete two score-building tasks from Daily Command or Score Booster.")
    if not proof_items:
        next_actions.append("Add your first portfolio or sample-work proof in Tracker.")
    if not next_actions:
        next_actions.append("Continue applying, tracking proof, and following up.")

    return {
        "user": {"id": user_id, "name": user.get("name", ""), "goal_daily": target, "plan": user.get("plan", "free")},
        "metrics": {
            "today_income": today_income,
            "today_target": target,
            "daily_progress_percent": daily_progress,
            "total_income": total_income,
            "proof_items": len(proof_items),
            "applications_tracked": len(apps),
            "prepared_applications": prepared_apps,
            "completed_tasks": completed_tasks,
            "projected_7_day": projected_7,
            "projected_30_day": projected_30
        },
        "proof_items": proof_items,
        "next_actions": next_actions,
        "forecast_note": "Forecast is based on current daily proof and target discipline. It is not a guarantee."
    }


@app.post("/api/earning-proof/{user_id}")
def add_earning_proof(user_id: int, source: str = Form(...), amount: int = Form(...), note: str = Form(""), proof_type: str = Form("income")):
    conn = db()
    conn.execute("INSERT INTO income (user_id, source, amount, note, created_at) VALUES (?, ?, ?, ?, ?)", (user_id, source, amount, f"[{proof_type}] {note}", now()))
    conn.commit()
    conn.close()
    return {"status": "saved", "message": "Earning/proof item saved and recruiter proof updated."}




def update_user_streak(user_id: int):
    today = datetime.now().date()
    conn = db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")

    last_active = user["last_active_date"] if "last_active_date" in user.keys() else ""
    streak = int(user["streak_days"] or 0) if "streak_days" in user.keys() else 0

    if last_active == today.isoformat():
        new_streak = streak
    else:
        try:
            last_date = datetime.fromisoformat(last_active).date() if last_active else None
        except Exception:
            last_date = None

        if last_date and (today - last_date).days == 1:
            new_streak = streak + 1
        else:
            new_streak = 1

    conn.execute("""
    UPDATE users SET streak_days=?, last_active_date=?, total_tasks_completed=COALESCE(total_tasks_completed,0)+1
    WHERE id=?
    """, (new_streak, today.isoformat(), user_id))
    conn.commit()
    conn.close()
    return new_streak


@app.post("/api/tasks/{task_id}/complete")
def complete_task(task_id: int):
    conn = db()
    task = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    if not task:
        conn.close()
        raise HTTPException(status_code=404, detail="Task not found")

    conn.execute("UPDATE tasks SET status='completed' WHERE id=?", (task_id,))
    conn.commit()
    conn.close()

    streak = update_user_streak(task["user_id"])
    return {
        "status": "completed",
        "task_id": task_id,
        "user_id": task["user_id"],
        "streak_days": streak,
        "message": "Task completed. Streak and activity score updated."
    }


@app.post("/api/tasks/{task_id}/reopen")
def reopen_task(task_id: int):
    conn = db()
    task = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    if not task:
        conn.close()
        raise HTTPException(status_code=404, detail="Task not found")
    conn.execute("UPDATE tasks SET status='pending' WHERE id=?", (task_id,))
    conn.commit()
    conn.close()
    return {"status": "reopened", "task_id": task_id}


@app.get("/api/execution-engine/{user_id}")
def execution_engine(user_id: int):
    user = get_user(user_id)
    conn = db()
    tasks = rows_to_dicts(conn.execute("SELECT * FROM tasks WHERE user_id=? ORDER BY id DESC LIMIT 25", (user_id,)).fetchall())

    if not tasks:
        default_tasks = [
            ("Complete Score Booster", "Open Score Booster and improve profile readiness.", 300),
            ("Prepare Top 10 jobs", "Use Jobs Engine and save top 10 matched opportunities.", 300),
            ("Add one proof item", "Add income, sample work, or portfolio proof in Income Dashboard.", 200),
            ("Open recruiter profile", "Review Talent Pool profile and missing actions.", 100),
            ("Send two follow-ups", "Follow up on saved or prepared applications.", 200)
        ]
        for title, desc, reward in default_tasks:
            conn.execute("INSERT INTO tasks (user_id, title, description, estimated_reward, status, created_at) VALUES (?, ?, ?, ?, 'pending', ?)", (user_id, title, desc, reward, now()))
        conn.commit()
        tasks = rows_to_dicts(conn.execute("SELECT * FROM tasks WHERE user_id=? ORDER BY id DESC LIMIT 25", (user_id,)).fetchall())

    today = datetime.now().date().isoformat()
    completed_today = [
        t for t in tasks
        if t.get("status") == "completed" and str(t.get("created_at", "")).startswith(today)
    ]
    pending = [t for t in tasks if t.get("status") != "completed"]
    completed = [t for t in tasks if t.get("status") == "completed"]

    streak = int(user.get("streak_days") or 0)
    total_completed = int(user.get("total_tasks_completed") or 0)

    streak_bonus = 0
    if streak >= 14:
        streak_bonus = 20
    elif streak >= 7:
        streak_bonus = 10
    elif streak >= 3:
        streak_bonus = 5

    execution_score = min(100, total_completed * 5 + streak * 4 + streak_bonus)

    daily_goal_tasks = 2
    daily_task_progress = min(100, round((len(completed_today) / daily_goal_tasks) * 100))

    if len(completed_today) >= daily_goal_tasks:
        daily_status = "Daily execution complete"
    elif len(completed_today) == 1:
        daily_status = "One more task to complete today's streak goal"
    else:
        daily_status = "Complete two tasks to protect your streak"

    return {
        "user": {
            "id": user_id,
            "name": user.get("name", ""),
            "streak_days": streak,
            "last_active_date": user.get("last_active_date", ""),
            "total_tasks_completed": total_completed
        },
        "metrics": {
            "execution_score": execution_score,
            "streak_bonus": streak_bonus,
            "daily_goal_tasks": daily_goal_tasks,
            "completed_today": len(completed_today),
            "daily_task_progress": daily_task_progress,
            "pending_tasks": len(pending),
            "completed_tasks": len(completed),
            "estimated_reward_pending": sum(int(t.get("estimated_reward") or 0) for t in pending)
        },
        "daily_status": daily_status,
        "tasks": tasks,
        "retention_rules": [
            "Complete at least 2 tasks daily",
            "Prepare jobs before applying",
            "Track proof after every small win",
            "Follow up after 3–5 days",
            "Improve recruiter proof weekly"
        ]
    }


@app.post("/api/execution-engine/create-task/{user_id}")
def create_execution_task(user_id: int, title: str = Form(...), description: str = Form(""), estimated_reward: int = Form(100)):
    get_user(user_id)
    conn = db()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO tasks (user_id, title, description, estimated_reward, status, created_at)
    VALUES (?, ?, ?, ?, 'pending', ?)
    """, (user_id, title, description, estimated_reward, now()))
    conn.commit()
    task_id = cur.lastrowid
    conn.close()
    return {"status": "created", "task_id": task_id}




def build_apply_proposal(user, job):
    name = user.get("name", "Candidate")
    headline = user.get("headline", "Zero2Earn candidate")
    skills = split_skills(user.get("skills"))
    top_skills = ", ".join(skills[:5]) if skills else "research, writing, remote work"
    title = job.get("title", "this role")
    company = job.get("company", "your team")
    category = job.get("category", "remote work")

    opener = f"Hello {company} team,"
    if any(w in title.lower() for w in ["medical", "health", "clinical", "patient", "doctor"]):
        body = f"I am interested in the {title} opportunity. My healthcare background, clinical understanding, and experience with medical writing/AI-assisted review make me a strong fit for work that needs accuracy, safety, and clear communication."
    else:
        body = f"I am interested in the {title} opportunity. My profile combines reliable execution, research ability, writing skill, and AI-assisted productivity."

    proof = f"My strongest relevant skills include: {top_skills}. I can support this role with structured work, timely delivery, and careful documentation."
    close = "I would be happy to discuss how I can contribute.\n\nRegards,\n" + name
    return f"{opener}\n\n{body}\n\n{proof}\n\n{close}"


def build_apply_cover_letter(user, job):
    name = user.get("name", "Candidate")
    title = job.get("title", "the role")
    company = job.get("company", "your organization")
    summary = user.get("summary") or "I bring practical experience, communication skills, and remote work readiness."
    return f"""Dear Hiring Manager,

I am applying for {title} at {company}.

{summary}

I am especially interested in this opportunity because it aligns with my skills and current career direction. I can bring accuracy, consistency, strong communication, and AI-assisted productivity to the role.

Thank you for your consideration.

Regards,
{name}"""


def build_followup_message(user, app_row):
    name = user.get("name", "Candidate")
    title = app_row.get("title", "the role")
    company = app_row.get("company", "your organization")
    return f"""Hello {company} team,

I wanted to politely follow up on my application for {title}. I remain very interested in the opportunity and would be happy to share any additional information if needed.

Regards,
{name}"""


@app.get("/api/apply-engine/plan/{user_id}")
def apply_engine_plan(user_id: int, min_score: int = 65, limit: int = 10):
    user = get_user(user_id)
    jobs = [j for j in build_job_cards(user) if int(j.get("score", 0)) >= min_score]
    jobs = sorted(jobs, key=lambda x: x["score"], reverse=True)[:limit]

    plan_items = []
    for j in jobs:
        proposal = build_apply_proposal(user, j)
        cover = build_apply_cover_letter(user, j)
        followup = f"Follow up after 3–5 days if no response from {j.get('company','company')}."
        plan_items.append({
            **j,
            "apply_decision": "Apply now" if j["score"] >= 75 else "Review then apply",
            "proposal": proposal,
            "cover_letter": cover,
            "follow_up_instruction": followup,
            "apply_steps": [
                "Open official portal",
                "Verify company and role",
                "Copy proposal/cover letter",
                "Submit application manually",
                "Return to Zero2Earn and click Mark Applied"
            ]
        })

    return {
        "mode": "Real Apply Engine",
        "min_score": min_score,
        "count": len(plan_items),
        "items": plan_items,
        "safety_rules": [
            "Never pay to apply",
            "Use official portals only",
            "Do not share OTP/password",
            "Avoid suspicious WhatsApp-only hiring",
            "Track every application and follow up after 3–5 days"
        ]
    }


@app.post("/api/apply-engine/prepare/{user_id}")
def apply_engine_prepare(user_id: int, min_score: int = Form(65), limit: int = Form(10)):
    user = get_user(user_id)
    plan = apply_engine_plan(user_id, min_score=min_score, limit=limit)["items"]
    conn = db()
    ensure_application_columns(conn)
    prepared = []
    for job in plan:
        proposal = build_apply_proposal(user, job)
        cover = build_apply_cover_letter(user, job)
        followup_text = f"Hello, I wanted to follow up on my application for {job['title']} at {job['company']}."
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO applications
        (user_id, job_id, title, company, url, score, status, proposal, cover_letter, follow_up, apply_source, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 'prepared', ?, ?, ?, ?, ?)
        """, (user_id, job["id"], job["title"], job["company"], job["url"], job["score"], proposal, cover, followup_text, job.get("source",""), now()))
        app_id = cur.lastrowid
        prepared.append({"application_id": app_id, **job})
    conn.commit()
    conn.close()
    return {"status": "prepared", "count": len(prepared), "items": prepared}


@app.post("/api/apply-engine/mark-applied/{application_id}")
def mark_application_applied(application_id: int):
    conn = db()
    ensure_application_columns(conn)
    row = conn.execute("SELECT * FROM applications WHERE id=?", (application_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Application not found")
    app_row = dict(row)
    applied_at = now()
    due = (datetime.now() + timedelta(days=4)).date().isoformat()
    conn.execute("""
    UPDATE applications SET status='applied', applied_at=?, follow_up_due=? WHERE id=?
    """, (applied_at, due, application_id))

    user = get_user(app_row["user_id"])
    message = build_followup_message(user, app_row)
    conn.execute("""
    INSERT INTO followups (user_id, application_id, title, company, due_date, message, status, created_at)
    VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
    """, (app_row["user_id"], application_id, app_row["title"], app_row["company"], due, message, now()))
    conn.commit()
    conn.close()
    try:
        daily_500_action(app_row["user_id"], action="jobs_applied", amount=1)
        first_100_action(app_row["user_id"], action="job_applied", amount=1)
    except Exception:
        pass
    return {
        "status": "applied",
        "application_id": application_id,
        "follow_up_due": due,
        "message": "Application marked applied and follow-up reminder created."
    }


@app.post("/api/apply-engine/status/{application_id}")
def update_application_status(application_id: int, status: str = Form(...), note: str = Form(""), income_value: int = Form(0)):
    allowed = ["prepared", "applied", "followed_up", "reply", "interview", "hired", "rejected", "closed"]
    if status not in allowed:
        raise HTTPException(status_code=400, detail="Invalid application status")
    conn = db()
    ensure_application_columns(conn)
    row = conn.execute("SELECT * FROM applications WHERE id=?", (application_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Application not found")
    conn.execute("""
    UPDATE applications SET status=?, reply_note=?, income_value=? WHERE id=?
    """, (status, note, income_value, application_id))
    if status == "hired" and income_value > 0:
        conn.execute("""
        INSERT INTO income (user_id, source, amount, note, created_at)
        VALUES (?, ?, ?, ?, ?)
        """, (row["user_id"], row["title"], income_value, f"[hired] {note}", now()))
    conn.commit()
    conn.close()
    return {"status": "updated", "application_id": application_id, "new_status": status}


@app.get("/api/apply-engine/tracker/{user_id}")
def apply_engine_tracker(user_id: int):
    conn = db()
    apps = rows_to_dicts(conn.execute("SELECT * FROM applications WHERE user_id=? ORDER BY id DESC", (user_id,)).fetchall())
    followups = rows_to_dicts(conn.execute("SELECT * FROM followups WHERE user_id=? ORDER BY due_date ASC, id DESC", (user_id,)).fetchall())
    conn.close()

    counts = {}
    for a in apps:
        counts[a.get("status", "unknown")] = counts.get(a.get("status", "unknown"), 0) + 1

    due_today = datetime.now().date().isoformat()
    due_followups = [f for f in followups if f.get("status") == "pending" and f.get("due_date", "") <= due_today]

    return {
        "counts": counts,
        "applications": apps,
        "followups": followups,
        "due_followups": due_followups,
        "metrics": {
            "total": len(apps),
            "applied": counts.get("applied", 0),
            "replies": counts.get("reply", 0),
            "interviews": counts.get("interview", 0),
            "hired": counts.get("hired", 0),
            "due_followups": len(due_followups)
        }
    }


@app.post("/api/apply-engine/followup/{followup_id}/done")
def mark_followup_done(followup_id: int):
    conn = db()
    row = conn.execute("SELECT * FROM followups WHERE id=?", (followup_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Follow-up not found")
    conn.execute("UPDATE followups SET status='sent' WHERE id=?", (followup_id,))
    conn.execute("UPDATE applications SET status='followed_up' WHERE id=?", (row["application_id"],))
    conn.commit()
    conn.close()
    return {"status": "sent", "followup_id": followup_id}



# ---------------- DAILY ₹500 EXECUTION MODE ----------------

def ensure_daily_execution_table():
    conn = db()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS daily_execution (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        execution_date TEXT,
        jobs_prepared INTEGER DEFAULT 0,
        jobs_applied INTEGER DEFAULT 0,
        micro_tasks INTEGER DEFAULT 0,
        followups_sent INTEGER DEFAULT 0,
        proof_added INTEGER DEFAULT 0,
        estimated_value INTEGER DEFAULT 0,
        status TEXT DEFAULT 'active',
        created_at TEXT DEFAULT '',
        updated_at TEXT DEFAULT ''
    )
    """)
    conn.commit()
    conn.close()


def get_or_create_daily_execution(user_id: int):
    ensure_daily_execution_table()
    today = datetime.now().date().isoformat()
    conn = db()
    row = conn.execute("SELECT * FROM daily_execution WHERE user_id=? AND execution_date=?", (user_id, today)).fetchone()
    if not row:
        conn.execute("""
        INSERT INTO daily_execution
        (user_id, execution_date, jobs_prepared, jobs_applied, micro_tasks, followups_sent, proof_added, estimated_value, status, created_at, updated_at)
        VALUES (?, ?, 0, 0, 0, 0, 0, 0, 'active', ?, ?)
        """, (user_id, today, now(), now()))
        conn.commit()
        row = conn.execute("SELECT * FROM daily_execution WHERE user_id=? AND execution_date=?", (user_id, today)).fetchone()
    conn.close()
    return dict(row)


def calculate_daily_500_summary(user_id: int):
    record = get_or_create_daily_execution(user_id)
    target = 500
    jobs_prepared = int(record.get("jobs_prepared") or 0)
    jobs_applied = int(record.get("jobs_applied") or 0)
    micro_tasks = int(record.get("micro_tasks") or 0)
    followups_sent = int(record.get("followups_sent") or 0)
    proof_added = int(record.get("proof_added") or 0)

    estimated_value = min(500, jobs_prepared * 20 + jobs_applied * 45 + micro_tasks * 100 + followups_sent * 35 + proof_added * 75)

    requirements = {
        "jobs_prepared": {"done": jobs_prepared, "target": 5, "label": "Prepare 5 strong jobs"},
        "jobs_applied": {"done": jobs_applied, "target": 5, "label": "Apply / mark 5 jobs applied"},
        "micro_tasks": {"done": micro_tasks, "target": 2, "label": "Complete 2 micro-income/proof tasks"},
        "followups_sent": {"done": followups_sent, "target": 2, "label": "Send 2 follow-ups"},
        "proof_added": {"done": proof_added, "target": 1, "label": "Add 1 proof/income item"}
    }

    completed_steps = sum(1 for r in requirements.values() if r["done"] >= r["target"])
    completion_percent = round((completed_steps / len(requirements)) * 100)
    money_percent = min(100, round((estimated_value / target) * 100))
    status = "complete" if completion_percent == 100 else "active"

    next_action = "Daily execution complete. Track real replies and income."
    for r in requirements.values():
        if r["done"] < r["target"]:
            next_action = r["label"]
            break

    conn = db()
    conn.execute("UPDATE daily_execution SET estimated_value=?, status=?, updated_at=? WHERE id=?", (estimated_value, status, now(), record["id"]))
    conn.commit()
    conn.close()

    return {
        "date": record["execution_date"],
        "target": target,
        "estimated_value": estimated_value,
        "money_percent": money_percent,
        "completion_percent": completion_percent,
        "status": status,
        "next_action": next_action,
        "requirements": requirements,
        "rules": [
            "This is an earning behavior engine, not a guaranteed income claim.",
            "Never pay to apply.",
            "Use official job portals only.",
            "Track every action.",
            "Follow up after 3–5 days."
        ]
    }


@app.get("/api/daily-500/{user_id}")
def daily_500(user_id: int):
    get_user(user_id)
    summary = calculate_daily_500_summary(user_id)
    conn = db()
    apps_today = rows_to_dicts(conn.execute("""
        SELECT * FROM applications
        WHERE user_id=? AND (created_at LIKE ? OR applied_at LIKE ?)
        ORDER BY id DESC LIMIT 20
    """, (user_id, summary["date"] + "%", summary["date"] + "%")).fetchall())
    conn.close()

    return {
        "mode": "Daily ₹500 Execution Mode",
        "summary": summary,
        "apps_today": apps_today,
        "steps": [
            {"step": 1, "title": "Prepare 5 jobs", "route": "apply", "button": "Open Apply Engine", "why": "Prepared jobs create ready-to-apply momentum."},
            {"step": 2, "title": "Mark 5 jobs applied", "route": "apply", "button": "Open Apply Tracker", "why": "Applications create reply probability."},
            {"step": 3, "title": "Complete 2 micro/proof tasks", "route": "micro", "button": "Open Micro Income", "why": "Backup earning tasks reduce waiting time."},
            {"step": 4, "title": "Send 2 follow-ups", "route": "apply", "button": "Open Follow-up Queue", "why": "Follow-ups increase response chance."},
            {"step": 5, "title": "Add 1 proof item", "route": "earning", "button": "Open Income Dashboard", "why": "Proof improves recruiter trust."}
        ]
    }


@app.post("/api/daily-500/action/{user_id}")
def daily_500_action(user_id: int, action: str = Form(...), amount: int = Form(1)):
    get_user(user_id)
    allowed = ["jobs_prepared", "jobs_applied", "micro_tasks", "followups_sent", "proof_added"]
    if action not in allowed:
        raise HTTPException(status_code=400, detail="Invalid daily action")
    record = get_or_create_daily_execution(user_id)
    conn = db()
    conn.execute(f"UPDATE daily_execution SET {action}=COALESCE({action},0)+?, updated_at=? WHERE id=?", (int(amount or 1), now(), record["id"]))
    conn.commit()
    conn.close()
    return {"status": "updated", "summary": calculate_daily_500_summary(user_id)}


@app.post("/api/daily-500/prepare-jobs/{user_id}")
def daily_500_prepare_jobs(user_id: int, limit: int = Form(5), min_score: int = Form(65)):
    result = apply_engine_prepare(user_id, min_score=min_score, limit=limit)
    record = get_or_create_daily_execution(user_id)
    conn = db()
    conn.execute("UPDATE daily_execution SET jobs_prepared=MAX(COALESCE(jobs_prepared,0), ?), updated_at=? WHERE id=?", (int(result.get("count", 0)), now(), record["id"]))
    conn.commit()
    conn.close()
    return {"status": "prepared", "prepared": result.get("count", 0), "summary": calculate_daily_500_summary(user_id)}


@app.post("/api/daily-500/reset-today/{user_id}")
def daily_500_reset_today(user_id: int):
    get_user(user_id)
    today = datetime.now().date().isoformat()
    ensure_daily_execution_table()
    conn = db()
    conn.execute("""
    UPDATE daily_execution
    SET jobs_prepared=0, jobs_applied=0, micro_tasks=0, followups_sent=0, proof_added=0,
        estimated_value=0, status='active', updated_at=?
    WHERE user_id=? AND execution_date=?
    """, (now(), user_id, today))
    conn.commit()
    conn.close()
    return {"status": "reset", "summary": calculate_daily_500_summary(user_id)}



# ---------------- GROQ REAL WINGMAN AI ----------------

def get_groq_client():
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key or api_key == "gsk_your_real_key_here":
        return None
    try:
        from groq import Groq
        return Groq(api_key=api_key)
    except Exception:
        return None


def groq_safe_text(value, limit=10000):
    return str(value or "").strip()[:limit]


def parse_json_object(text):
    import json
    raw = str(text or "").strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.replace("json\n", "", 1).replace("JSON\n", "", 1)
    try:
        return json.loads(raw)
    except Exception:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(raw[start:end+1])
            except Exception:
                return None
    return None


def groq_fallback_wingman(user, title, company, description):
    skills = split_skills(user.get("skills"))
    top_skills = ", ".join(skills[:6]) if skills else "research, writing, communication, documentation"
    name = user.get("name") or "Candidate"
    headline = user.get("headline") or "Zero2Earn candidate"

    proposal = f"""Hello {company or 'Hiring Team'},

I am interested in the {title or 'role'}.

My profile combines {top_skills}. I can support this opportunity with accuracy, clear communication, structured execution, and reliable delivery.

Regards,
{name}"""

    cover_letter = f"""Dear Hiring Manager,

I am applying for the {title or 'available'} role at {company or 'your organization'}.

My current positioning is: {headline}. I can contribute through accuracy, responsibility, communication, and consistent execution.

Thank you for considering my application.

Regards,
{name}"""

    follow_up = f"""Hello {company or 'Hiring Team'},

I wanted to politely follow up on my application for the {title or 'role'}. I remain interested and would be happy to share any additional details if needed.

Regards,
{name}"""

    return {
        "mode": "fallback_template",
        "match_score": 68,
        "win_chance": 62,
        "matched_skills": skills[:6],
        "missing_skills": ["Add job-specific proof or portfolio sample if available"],
        "match_reasons": [
            "Generated from saved profile/resume keywords",
            "Fallback used because GROQ_API_KEY is missing/invalid or Groq call failed",
            "Customize before final submission"
        ],
        "proposal": proposal,
        "cover_letter": cover_letter,
        "follow_up": follow_up,
        "interview_pitch": f"I am {name}. My strengths include {top_skills}. I am looking for practical work where I can contribute with accuracy, communication, and consistent execution.",
        "warnings": ["Fallback mode. Set GROQ_API_KEY for real AI output."]
    }


@app.get("/api/wingman/groq-health")
def wingman_groq_health():
    key = os.getenv("GROQ_API_KEY", "").strip()
    return {
        "groq_key_configured": bool(key and key != "gsk_your_real_key_here"),
        "model": os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
        "mode": "ai_ready" if key and key != "gsk_your_real_key_here" else "fallback_template"
    }


@app.post("/api/wingman/groq-generate/{user_id}")
def wingman_groq_generate(
    user_id: int,
    title: str = Form(""),
    company: str = Form(""),
    description: str = Form(""),
    url: str = Form(""),
    salary: str = Form(""),
    tone: str = Form("professional")
):
    user = get_user(user_id)

    title = (title or "").strip()
    company = (company or "").strip()
    description = (description or "").strip()

    if len(description) < 80:
        raise HTTPException(
            status_code=400,
            detail="Paste a full job description first. Wingman needs responsibilities and requirements to generate useful output."
        )

    client = get_groq_client()
    if not client:
        fallback = groq_fallback_wingman(user, title, company, description)
        fallback["warnings"] = ["GROQ_API_KEY missing or invalid. Using fallback template."]
        return fallback

    skills = split_skills(user.get("skills"))
    resume = groq_safe_text(user.get("resume_text") or user.get("summary") or "", 9000)

    system_prompt = """
You are Zero2Earn Wingman, a recruiter-grade job application assistant.

STRICT RULES:
- Use ONLY the provided user profile/resume and job description.
- Do NOT invent degrees, employers, certifications, salary, experience, or achievements.
- Do NOT say "job description is not provided" because it is provided.
- Do NOT provide explanation outside JSON.
- Return valid JSON only.
- match_score and win_chance MUST be integers from 0 to 100.
- proposal must be a ready-to-send message, not a meta description of what you will write.
- cover_letter must be a complete letter.
- follow_up must be a complete polite follow-up.
- interview_pitch must be a 30-second candidate intro.
"""

    user_prompt = f"""
USER PROFILE
Name: {user.get('name','')}
Headline: {user.get('headline','')}
Summary: {user.get('summary','')}
Skills: {', '.join(skills)}
Resume:
{resume}

JOB DETAILS
Title: {title}
Company: {company}
Pay: {salary}
URL: {url}
Full Job Description:
{groq_safe_text(description, 8000)}

Tone: {tone}

TASK:
1. Match the user's profile to the job.
2. Create job-specific application material.
3. Identify matched skills and missing skills.
4. Score fit realistically.

OUTPUT FORMAT — VALID JSON ONLY:
{{
  "mode": "groq_ai",
  "match_score": 82,
  "win_chance": 74,
  "matched_skills": ["skill 1", "skill 2"],
  "missing_skills": ["gap 1", "gap 2"],
  "match_reasons": ["reason 1", "reason 2", "reason 3"],
  "proposal": "ready-to-send proposal here",
  "cover_letter": "complete cover letter here",
  "follow_up": "complete follow-up message here",
  "interview_pitch": "30-second candidate pitch here",
  "warnings": ["honest caution if needed"]
}}
"""

    try:
        model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt.strip()},
                {"role": "user", "content": user_prompt.strip()}
            ],
            temperature=0.25,
            max_tokens=1800,
            response_format={"type": "json_object"}
        )

        text = completion.choices[0].message.content
        data = parse_json_object(text)
        if not data:
            fallback = groq_fallback_wingman(user, title, company, description)
            fallback["warnings"].append("Groq returned invalid JSON. Fallback used.")
            return fallback

        # Normalize scores: some models may return 0.82 or "82%".
        def normalize_score(value, default):
            try:
                if isinstance(value, str):
                    value = value.replace("%", "").strip()
                value = float(value)
                if value <= 1:
                    value = value * 100
                return max(0, min(100, int(round(value))))
            except Exception:
                return default

        data["match_score"] = normalize_score(data.get("match_score"), 65)
        data["win_chance"] = normalize_score(data.get("win_chance"), 55)

        # Ensure arrays.
        for key in ["matched_skills", "missing_skills", "match_reasons", "warnings"]:
            if not isinstance(data.get(key), list):
                data[key] = []

        # Ensure required text fields.
        for key in ["proposal", "cover_letter", "follow_up", "interview_pitch"]:
            if not str(data.get(key, "")).strip():
                fallback = groq_fallback_wingman(user, title, company, description)
                fallback["warnings"].append(f"Groq response missing {key}. Fallback used.")
                return fallback

        data["mode"] = "groq_ai"
        return data

    except Exception as e:
        fallback = groq_fallback_wingman(user, title, company, description)
        fallback["warnings"].append(f"Groq call failed: {str(e)[:180]}")
        return fallback


@app.post("/api/wingman/groq-save/{user_id}")
def wingman_groq_save(
    user_id: int,
    job_id: str = Form(""),
    title: str = Form(""),
    company: str = Form(""),
    url: str = Form(""),
    score: int = Form(0),
    proposal: str = Form(""),
    cover_letter: str = Form(""),
    follow_up: str = Form("")
):
    get_user(user_id)
    conn = db()
    try:
        if "ensure_application_columns" in globals():
            ensure_application_columns(conn)
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO applications
        (user_id, job_id, title, company, url, score, status, proposal, cover_letter, follow_up, apply_source, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 'saved', ?, ?, ?, ?, ?)
        """, (
            user_id,
            job_id or "",
            title or "Untitled role",
            company or "Unknown company",
            url or "#",
            int(score or 0),
            proposal or "",
            cover_letter or "",
            follow_up or "",
            "groq_wingman",
            now()
        ))
        conn.commit()
        return {"status": "saved", "application_id": cur.lastrowid, "message": "Groq Wingman output saved to tracker"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Groq Wingman save failed: {str(e)}")
    finally:
        conn.close()



# ---------------- INTERACTIVE MODULE SUPPORT ----------------

@app.post("/api/micro-jobs/track/{user_id}")
def track_micro_job(user_id: int, platform: str = Form(...), amount: int = Form(100), note: str = Form("")):
    get_user(user_id)
    conn = db()
    conn.execute(
        "INSERT INTO income (user_id, source, amount, note, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, platform, int(amount or 0), f"[micro] {note}", now())
    )
    conn.commit()
    conn.close()
    try:
        if "daily_500_action" in globals():
            daily_500_action(user_id, action="micro_tasks", amount=1)
    except Exception:
        pass
    return {"status": "tracked", "message": "Micro task tracked and proof added."}


@app.post("/api/skills/complete-day/{user_id}")
def complete_skill_day(user_id: int, day: int = Form(...), title: str = Form("Skill task"), note: str = Form("")):
    get_user(user_id)
    conn = db()
    conn.execute(
        "INSERT INTO tasks (user_id, title, description, estimated_reward, status, created_at) VALUES (?, ?, ?, ?, 'completed', ?)",
        (user_id, f"Skill Day {day}: {title}", note or "Completed skill improvement task.", 100, now())
    )
    conn.commit()
    conn.close()
    return {"status": "completed", "message": f"Skill day {day} marked complete."}


@app.post("/api/automation/run-daily/{user_id}")
def run_daily_automation(user_id: int):
    get_user(user_id)
    # This is a safe automation planner, not auto-applying.
    return {
        "status": "ready",
        "commands": [
            "Prepare 5 resume-matched jobs.",
            "Use Wingman for 2 strongest jobs.",
            "Apply manually using official portals.",
            "Track every application.",
            "Send due follow-ups.",
            "Complete 1 micro-income task if no replies."
        ],
        "message": "Daily automation plan generated."
    }



# ---------------- FIRST ₹100 MISSION + REAL MICRO PORTALS ----------------

def micro_portal_catalog():
    return [
        {
            "name": "UserTesting",
            "category": "Website/App Testing",
            "earn_estimate": "₹500–₹3,000 per test when approved",
            "first_100_path": "Apply, complete profile, qualify for first short test.",
            "speed": "Medium",
            "difficulty": "Medium",
            "url": "https://www.usertesting.com/get-paid-to-test",
            "trust_note": "Official contributor program; no payment to join.",
            "best_for": "English speaking, product feedback, website testing"
        },
        {
            "name": "Toloka",
            "category": "AI Microtasks",
            "earn_estimate": "Small tasks; realistic first target ₹50–₹200",
            "first_100_path": "Sign up, complete training, finish simple AI/data tasks.",
            "speed": "Fast",
            "difficulty": "Easy",
            "url": "https://toloka.ai/tolokers",
            "trust_note": "Official Toloka tasker platform.",
            "best_for": "Data tasks, image/text evaluation"
        },
        {
            "name": "Clickworker",
            "category": "Microtasks/UHRS",
            "earn_estimate": "Varies; first target ₹100 after onboarding/tasks",
            "first_100_path": "Create account, complete assessments, check available tasks.",
            "speed": "Fast/Medium",
            "difficulty": "Easy/Medium",
            "url": "https://www.clickworker.com/clickworker/",
            "trust_note": "Official Clickworker worker signup.",
            "best_for": "UHRS, small online tasks, data work"
        },
        {
            "name": "OneForma",
            "category": "AI/Data Projects",
            "earn_estimate": "Project-based; first target after qualification",
            "first_100_path": "Create profile, apply to simple data/language projects.",
            "speed": "Medium",
            "difficulty": "Medium",
            "url": "https://www.oneforma.com/jobs/",
            "trust_note": "Official OneForma jobs portal.",
            "best_for": "AI data, language, annotation, evaluation"
        },
        {
            "name": "uTest",
            "category": "Software Testing",
            "earn_estimate": "Varies by test cycle; can exceed ₹100 per accepted bug/test",
            "first_100_path": "Join, complete Academy, join test cycles.",
            "speed": "Medium",
            "difficulty": "Medium",
            "url": "https://www.utest.com/tester-signup",
            "trust_note": "Official tester signup.",
            "best_for": "App testing, bug reporting"
        },
        {
            "name": "TestingTime",
            "category": "Paid User Research",
            "earn_estimate": "Study-based; often higher than ₹100 when selected",
            "first_100_path": "Create profile and apply to matching studies.",
            "speed": "Slow/Medium",
            "difficulty": "Easy",
            "url": "https://www.testingtime.com/en/become-a-paid-testuser/",
            "trust_note": "Official paid test user program.",
            "best_for": "User interviews and research studies"
        },
        {
            "name": "Prolific",
            "category": "Research Studies",
            "earn_estimate": "Study-based; first ₹100 possible after approval/studies",
            "first_100_path": "Join waitlist/signup, complete profile, take studies.",
            "speed": "Slow/Medium",
            "difficulty": "Easy",
            "url": "https://www.prolific.com/",
            "trust_note": "Research participation platform.",
            "best_for": "Academic/industry studies"
        },
        {
            "name": "Remotasks",
            "category": "AI Training Tasks",
            "earn_estimate": "Task/project-based; first target ₹100 after training",
            "first_100_path": "Sign up, complete training, start available tasks.",
            "speed": "Medium",
            "difficulty": "Medium",
            "url": "https://www.remotasks.com/en",
            "trust_note": "Official tasker platform; training required.",
            "best_for": "Image/video/data annotation"
        },
        {
            "name": "DataAnnotation",
            "category": "AI Training",
            "earn_estimate": "Qualification-based; higher potential if accepted",
            "first_100_path": "Apply and complete qualification tests.",
            "speed": "Slow",
            "difficulty": "Hard",
            "url": "https://www.dataannotation.tech/",
            "trust_note": "Never pay for certification or access.",
            "best_for": "Strong writing/reasoning contributors"
        },
        {
            "name": "TELUS International AI",
            "category": "AI Evaluation",
            "earn_estimate": "Part-time project-based; not instant but genuine",
            "first_100_path": "Apply to AI community roles and complete qualification.",
            "speed": "Slow",
            "difficulty": "Medium/Hard",
            "url": "https://www.telusinternational.com/careers/ai-community",
            "trust_note": "Official AI community jobs page.",
            "best_for": "Search/social/media evaluation"
        },
        {
            "name": "Appen",
            "category": "AI/Data Projects",
            "earn_estimate": "Project-based; varies by country/project",
            "first_100_path": "Create profile and apply to available projects.",
            "speed": "Slow/Medium",
            "difficulty": "Medium",
            "url": "https://appen.com/jobs/",
            "trust_note": "Official jobs page.",
            "best_for": "AI data, search evaluation, language tasks"
        },
        {
            "name": "Respondent",
            "category": "Paid Research Interviews",
            "earn_estimate": "Higher-value studies if selected",
            "first_100_path": "Create profile and apply to studies matching your background.",
            "speed": "Slow",
            "difficulty": "Medium",
            "url": "https://www.respondent.io/respondents",
            "trust_note": "Use official site only.",
            "best_for": "Professional research interviews"
        }
    ]


def ensure_first100_table():
    conn = db()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS first100_mission (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        mission_date TEXT DEFAULT '',
        micro_started INTEGER DEFAULT 0,
        micro_tracked INTEGER DEFAULT 0,
        job_prepared INTEGER DEFAULT 0,
        job_applied INTEGER DEFAULT 0,
        proof_added INTEGER DEFAULT 0,
        estimated_value INTEGER DEFAULT 0,
        completed INTEGER DEFAULT 0,
        created_at TEXT DEFAULT '',
        updated_at TEXT DEFAULT ''
    )
    """)
    conn.commit()
    conn.close()


def get_or_create_first100(user_id: int):
    ensure_first100_table()
    today = datetime.now().date().isoformat()
    conn = db()
    row = conn.execute("SELECT * FROM first100_mission WHERE user_id=? AND mission_date=?", (user_id, today)).fetchone()
    if not row:
        conn.execute("""
        INSERT INTO first100_mission
        (user_id, mission_date, micro_started, micro_tracked, job_prepared, job_applied, proof_added, estimated_value, completed, created_at, updated_at)
        VALUES (?, ?, 0, 0, 0, 0, 0, 0, 0, ?, ?)
        """, (user_id, today, now(), now()))
        conn.commit()
        row = conn.execute("SELECT * FROM first100_mission WHERE user_id=? AND mission_date=?", (user_id, today)).fetchone()
    conn.close()
    return dict(row)


def calculate_first100_summary(user_id: int):
    row = get_or_create_first100(user_id)
    micro_started = int(row.get("micro_started") or 0)
    micro_tracked = int(row.get("micro_tracked") or 0)
    job_prepared = int(row.get("job_prepared") or 0)
    job_applied = int(row.get("job_applied") or 0)
    proof_added = int(row.get("proof_added") or 0)

    estimated = min(100, micro_started * 10 + micro_tracked * 40 + job_prepared * 10 + job_applied * 20 + proof_added * 30)
    steps = {
        "micro_started": {"done": micro_started, "target": 1, "label": "Open 1 genuine micro-income platform"},
        "micro_tracked": {"done": micro_tracked, "target": 1, "label": "Complete/track 1 micro task"},
        "job_prepared": {"done": job_prepared, "target": 1, "label": "Prepare 1 job with Wingman"},
        "job_applied": {"done": job_applied, "target": 1, "label": "Apply/mark 1 job applied"},
        "proof_added": {"done": proof_added, "target": 1, "label": "Add ₹100 proof or practice proof"}
    }
    completed_steps = sum(1 for s in steps.values() if s["done"] >= s["target"])
    completed = 1 if completed_steps == len(steps) or estimated >= 100 else 0

    conn = db()
    conn.execute(
        "UPDATE first100_mission SET estimated_value=?, completed=?, updated_at=? WHERE id=?",
        (estimated, completed, now(), row["id"])
    )
    conn.commit()
    conn.close()

    next_action = "Mission complete — share proof and continue Daily ₹500 Mode."
    for s in steps.values():
        if s["done"] < s["target"]:
            next_action = s["label"]
            break

    return {
        "target": 100,
        "estimated_value": estimated,
        "progress_percent": min(100, estimated),
        "completed": bool(completed),
        "next_action": next_action,
        "steps": steps,
        "safety_rules": [
            "Never pay registration, deposit, upgrade, VIP, tax, wallet, or training fees.",
            "Avoid Telegram/WhatsApp prepaid task scams.",
            "Use official platform links only.",
            "Treat earnings as possible, not guaranteed.",
            "Track proof only after real work or verified practice completion."
        ]
    }


@app.get("/api/first-100/{user_id}")
def first_100(user_id: int):
    get_user(user_id)
    summary = calculate_first100_summary(user_id)
    return {
        "mode": "First ₹100 Mission",
        "summary": summary,
        "portals": micro_portal_catalog(),
        "mission_steps": [
            {"step": 1, "title": "Open a genuine portal", "action": "Choose Toloka, Clickworker, UserTesting, OneForma or uTest."},
            {"step": 2, "title": "Complete one small action", "action": "Signup, assessment, profile setup, or first available task."},
            {"step": 3, "title": "Prepare one job", "action": "Use Wingman on one resume-matched job."},
            {"step": 4, "title": "Apply or track", "action": "Apply manually on official portal and mark applied."},
            {"step": 5, "title": "Add proof", "action": "Add ₹100 income/proof or valid completion proof."}
        ]
    }


@app.post("/api/first-100/action/{user_id}")
def first_100_action(user_id: int, action: str = Form(...), amount: int = Form(1), note: str = Form("")):
    get_user(user_id)
    allowed = ["micro_started", "micro_tracked", "job_prepared", "job_applied", "proof_added"]
    if action not in allowed:
        raise HTTPException(status_code=400, detail="Invalid mission action")

    row = get_or_create_first100(user_id)
    conn = db()
    conn.execute(f"UPDATE first100_mission SET {action}=COALESCE({action},0)+?, updated_at=? WHERE id=?", (int(amount or 1), now(), row["id"]))
    if action in ["micro_tracked", "proof_added"]:
        conn.execute(
            "INSERT INTO income (user_id, source, amount, note, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, "First ₹100 Mission", 100 if action == "proof_added" else 50, note or f"[first100] {action}", now())
        )
    conn.commit()
    conn.close()
    return {"status": "updated", "summary": calculate_first100_summary(user_id)}


@app.post("/api/first-100/reset/{user_id}")
def first_100_reset(user_id: int):
    get_user(user_id)
    today = datetime.now().date().isoformat()
    ensure_first100_table()
    conn = db()
    conn.execute("""
    UPDATE first100_mission
    SET micro_started=0, micro_tracked=0, job_prepared=0, job_applied=0, proof_added=0,
        estimated_value=0, completed=0, updated_at=?
    WHERE user_id=? AND mission_date=?
    """, (now(), user_id, today))
    conn.commit()
    conn.close()
    return {"status": "reset", "summary": calculate_first100_summary(user_id)}




# ---------------- AI + RAZORPAY + UPGRADE SYSTEM ----------------

def razorpay_ready():
    return bool(os.getenv("RAZORPAY_KEY_ID")) and bool(os.getenv("RAZORPAY_KEY_SECRET"))

def get_razorpay_client():
    if not razorpay_ready():
        return None
    return razorpay.Client(auth=(os.getenv("RAZORPAY_KEY_ID"), os.getenv("RAZORPAY_KEY_SECRET")))

def pro_price():
    try:
        return int(os.getenv("ZERO2EARN_PRO_PRICE", "29900"))
    except Exception:
        return 29900

def is_pro_user(user):
    plan = (user.get("plan") or "free").lower()
    if plan in ["company", "college"]:
        return True
    if plan != "pro":
        return False
    pro_until = user.get("pro_until") or ""
    if not pro_until:
        return True
    try:
        return datetime.fromisoformat(pro_until) >= datetime.now()
    except Exception:
        return True

def ensure_saas_tables():
    conn = db()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        razorpay_order_id TEXT DEFAULT '',
        razorpay_payment_id TEXT DEFAULT '',
        razorpay_signature TEXT DEFAULT '',
        amount INTEGER DEFAULT 0,
        currency TEXT DEFAULT 'INR',
        status TEXT DEFAULT 'created',
        plan TEXT DEFAULT 'pro',
        created_at TEXT DEFAULT '',
        verified_at TEXT DEFAULT ''
    )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS ai_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        feature TEXT DEFAULT 'wingman',
        created_at TEXT DEFAULT ''
    )
    """)
    conn.commit()
    conn.close()

def free_ai_limit():
    try:
        return int(os.getenv("ZERO2EARN_FREE_AI_LIMIT", "3"))
    except Exception:
        return 3

def ai_usage_today(user_id: int, feature: str = "wingman"):
    ensure_saas_tables()
    today = datetime.now().date().isoformat()
    conn = db()
    row = conn.execute(
        "SELECT COUNT(*) c FROM ai_usage WHERE user_id=? AND feature=? AND created_at LIKE ?",
        (user_id, feature, today + "%")
    ).fetchone()
    conn.close()
    return int(row["c"] or 0)

def record_ai_usage(user_id: int, feature: str = "wingman"):
    ensure_saas_tables()
    conn = db()
    conn.execute("INSERT INTO ai_usage (user_id, feature, created_at) VALUES (?, ?, ?)", (user_id, feature, now()))
    conn.commit()
    conn.close()

def upgrade_trigger_for_user(user_id: int):
    user = get_user(user_id)
    if is_pro_user(user):
        return {"show": False, "reason": "already_pro", "message": "Pro active"}
    used = ai_usage_today(user_id, "wingman")
    first100_done = False
    try:
        first100_done = bool(calculate_first100_summary(user_id).get("completed"))
    except Exception:
        first100_done = False
    if used >= free_ai_limit():
        return {"show": True, "reason": "ai_limit", "message": "Free AI Wingman limit reached. Upgrade to Pro for unlimited proposal flow.", "cta": "Upgrade to Pro ₹299"}
    if first100_done:
        return {"show": True, "reason": "first100_complete", "message": "First ₹100 Mission complete. Unlock Daily ₹500 execution with Pro.", "cta": "Unlock Pro ₹299"}
    return {"show": False, "reason": "not_ready", "message": "Keep building proof."}

def groq_ready():
    return bool(os.getenv("GROQ_API_KEY")) and Groq is not None

def get_groq_client():
    if not groq_ready():
        return None
    return Groq(api_key=os.getenv("GROQ_API_KEY"))

def normalize_ai_score(v, default=65):
    try:
        if isinstance(v, str):
            v = v.replace("%", "").strip()
        v = float(v)
        if v <= 1:
            v *= 100
        return max(0, min(100, int(round(v))))
    except Exception:
        return default

def parse_ai_json(text):
    try:
        s = text.find("{")
        e = text.rfind("}")
        if s >= 0 and e > s:
            return json.loads(text[s:e+1])
    except Exception:
        pass
    return None

def fallback_ai_wingman(user, title, company, description):
    skills = split_skills(user.get("skills"))
    top = ", ".join(skills[:6]) if skills else "research, writing, communication, AI tools"
    title = title or "this role"
    company = company or "your organization"
    return {
        "mode": "fallback",
        "match_score": 70,
        "win_chance": 55,
        "matched_skills": skills[:8],
        "missing_skills": ["Add portfolio proof", "Tailor examples to the job"],
        "match_reasons": ["Generated from saved profile and job description", "Fallback used if GROQ_API_KEY is missing"],
        "proposal": f"Hello {company} team,\\n\\nI am interested in the {title} opportunity. My background includes {top}. I can support this work with accuracy, reliability, and AI-assisted productivity.\\n\\nRegards,\\n{user.get('name','Candidate')}",
        "cover_letter": f"Dear Hiring Manager,\\n\\nI am applying for {title} at {company}. I bring relevant experience, disciplined execution, and strong communication. I would be glad to contribute to your team.\\n\\nRegards,\\n{user.get('name','Candidate')}",
        "follow_up": f"Hello {company} team, I wanted to politely follow up on my application for {title}. I remain interested and available to discuss.",
        "interview_pitch": f"I am {user.get('name','a candidate')} with strengths in {top}. I can contribute with accuracy, speed, and clear communication.",
        "warnings": ["Fallback mode. Configure GROQ_API_KEY for real AI generation."]
    }

@app.get("/api/env/status")
def env_status():
    return {
        "razorpay_key_id_configured": bool(os.getenv("RAZORPAY_KEY_ID")),
        "razorpay_key_secret_configured": bool(os.getenv("RAZORPAY_KEY_SECRET")),
        "razorpay_mode": "live" if str(os.getenv("RAZORPAY_KEY_ID","")).startswith("rzp_live_") else "test" if str(os.getenv("RAZORPAY_KEY_ID","")).startswith("rzp_test_") else "not_configured",
        "pro_price_paise": pro_price(),
        "pro_price_rupees": round(pro_price()/100, 2),
        "groq_key_configured": bool(os.getenv("GROQ_API_KEY")),
        "free_ai_limit": free_ai_limit()
    }

@app.get("/api/billing/status/{user_id}")
def billing_status(user_id: int):
    user = get_user(user_id)
    return {
        "plan": user.get("plan", "free"),
        "pro_until": user.get("pro_until", ""),
        "is_pro": is_pro_user(user),
        "razorpay_ready": razorpay_ready(),
        "key_id": os.getenv("RAZORPAY_KEY_ID", ""),
        "price_paise": pro_price(),
        "price_rupees": round(pro_price()/100, 2),
        "ai_usage_today": ai_usage_today(user_id, "wingman"),
        "free_ai_limit": free_ai_limit(),
        "upgrade_trigger": upgrade_trigger_for_user(user_id)
    }

@app.post("/api/payment/create-order/{user_id}")
def create_payment_order(user_id: int):
    get_user(user_id)
    client = get_razorpay_client()
    if not client:
        raise HTTPException(status_code=500, detail="Razorpay keys are not configured")
    amount = pro_price()
    ensure_saas_tables()
    try:
        order = client.order.create({
            "amount": amount,
            "currency": "INR",
            "receipt": f"z2e_pro_{user_id}_{int(datetime.now().timestamp())}",
            "payment_capture": 1,
            "notes": {"user_id": str(user_id), "plan": "pro"}
        })
        conn = db()
        conn.execute(
            "INSERT INTO payments (user_id, razorpay_order_id, amount, currency, status, plan, created_at) VALUES (?, ?, ?, 'INR', 'created', 'pro', ?)",
            (user_id, order["id"], amount, now())
        )
        conn.commit()
        conn.close()
        return {"status": "created", "key_id": os.getenv("RAZORPAY_KEY_ID"), "order_id": order["id"], "amount": amount, "currency": "INR"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Razorpay order creation failed: {str(e)}")

@app.post("/api/payment/verify/{user_id}")
def verify_payment(user_id: int, razorpay_order_id: str = Form(...), razorpay_payment_id: str = Form(...), razorpay_signature: str = Form(...)):
    get_user(user_id)
    client = get_razorpay_client()
    if not client:
        raise HTTPException(status_code=500, detail="Razorpay keys are not configured")
    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature
        })
        pro_until = (datetime.now() + timedelta(days=30)).isoformat(timespec="seconds")
        ensure_saas_tables()
        conn = db()
        conn.execute("UPDATE users SET plan='pro', pro_until=? WHERE id=?", (pro_until, user_id))
        conn.execute("UPDATE payments SET razorpay_payment_id=?, razorpay_signature=?, status='paid', verified_at=? WHERE user_id=? AND razorpay_order_id=?", (razorpay_payment_id, razorpay_signature, now(), user_id, razorpay_order_id))
        conn.commit()
        conn.close()
        return {"status": "success", "message": "Payment verified. Pro activated.", "plan": "pro", "pro_until": pro_until}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Payment verification failed: {str(e)}")

@app.post("/api/payment/webhook")
async def razorpay_webhook(request: Request):
    secret = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")
    if secret:
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise HTTPException(status_code=400, detail="Invalid webhook signature")
    payload = json.loads(body.decode("utf-8"))
    event = payload.get("event", "")
    payment = payload.get("payload", {}).get("payment", {}).get("entity", {})
    order_id = payment.get("order_id", "")
    payment_id = payment.get("id", "")
    if event in ["payment.captured", "order.paid"] and order_id:
        ensure_saas_tables()
        conn = db()
        row = conn.execute("SELECT * FROM payments WHERE razorpay_order_id=? ORDER BY id DESC", (order_id,)).fetchone()
        if row:
            pro_until = (datetime.now() + timedelta(days=30)).isoformat(timespec="seconds")
            conn.execute("UPDATE users SET plan='pro', pro_until=? WHERE id=?", (pro_until, row["user_id"]))
            conn.execute("UPDATE payments SET razorpay_payment_id=?, status='paid', verified_at=? WHERE razorpay_order_id=?", (payment_id, now(), order_id))
            conn.commit()
        conn.close()
    return {"status": "ok"}

@app.get("/api/upgrade-trigger/{user_id}")
def upgrade_trigger(user_id: int):
    return upgrade_trigger_for_user(user_id)

@app.get("/api/wingman/ai-health")
def ai_health():
    return {"groq_key_configured": bool(os.getenv("GROQ_API_KEY")), "groq_library_available": Groq is not None, "mode": "ai_ready" if groq_ready() else "fallback_ready", "model": os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")}

@app.post("/api/wingman/ai-generate/{user_id}")
def wingman_ai_generate(user_id: int, title: str = Form(""), company: str = Form(""), description: str = Form(""), url: str = Form(""), salary: str = Form(""), tone: str = Form("professional")):
    user = get_user(user_id)
    if not is_pro_user(user) and ai_usage_today(user_id, "wingman") >= free_ai_limit():
        raise HTTPException(status_code=402, detail={"message": "Free AI Wingman limit reached. Upgrade to Pro.", "upgrade_trigger": upgrade_trigger_for_user(user_id)})
    if len((description or "").strip()) < 40:
        raise HTTPException(status_code=400, detail="Paste full job description first.")
    client = get_groq_client()
    if not client:
        data = fallback_ai_wingman(user, title, company, description)
        data["upgrade_trigger"] = upgrade_trigger_for_user(user_id)
        return data
    prompt = f"""Return valid JSON only. Create job-specific application material.

User:
Name: {user.get('name','')}
Headline: {user.get('headline','')}
Summary: {user.get('summary','')}
Skills: {user.get('skills','')}
Resume: {(user.get('resume_text') or '')[:5000]}

Job:
Title: {title}
Company: {company}
Salary: {salary}
URL: {url}
Description: {description[:6000]}

JSON fields:
mode, match_score, win_chance, matched_skills, missing_skills, match_reasons, proposal, cover_letter, follow_up, interview_pitch, warnings.
"""
    try:
        res = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.25,
            max_tokens=1800,
            response_format={"type": "json_object"}
        )
        data = parse_ai_json(res.choices[0].message.content) or fallback_ai_wingman(user, title, company, description)
        data["match_score"] = normalize_ai_score(data.get("match_score"), 70)
        data["win_chance"] = normalize_ai_score(data.get("win_chance"), 55)
        data["mode"] = "groq_ai"
        record_ai_usage(user_id, "wingman")
        data["ai_usage_today"] = ai_usage_today(user_id, "wingman")
        data["free_ai_limit"] = free_ai_limit()
        data["upgrade_trigger"] = upgrade_trigger_for_user(user_id)
        return data
    except Exception as e:
        data = fallback_ai_wingman(user, title, company, description)
        data["warnings"].append(f"Groq failed: {str(e)[:160]}")
        data["upgrade_trigger"] = upgrade_trigger_for_user(user_id)
        return data



# ---------------- AUTO CONVERSION ENGINE + TELEGRAM NOTIFICATIONS ----------------

def ensure_conversion_tables():
    conn = db()
    cur = conn.cursor()
    for col, definition in {
        "telegram_chat_id": "TEXT DEFAULT ''",
        "telegram_username": "TEXT DEFAULT ''",
        "whatsapp_number": "TEXT DEFAULT ''",
        "notification_opt_in": "INTEGER DEFAULT 1",
        "last_daily_alert_at": "TEXT DEFAULT ''",
        "last_upgrade_nudge_at": "TEXT DEFAULT ''"
    }.items():
        try:
            add_column(cur, "users", col, definition)
        except Exception:
            pass

    cur.execute("""
    CREATE TABLE IF NOT EXISTS conversion_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        event_type TEXT DEFAULT '',
        source TEXT DEFAULT '',
        message TEXT DEFAULT '',
        metadata TEXT DEFAULT '',
        created_at TEXT DEFAULT ''
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS notification_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        channel TEXT DEFAULT 'telegram',
        event_type TEXT DEFAULT '',
        message TEXT DEFAULT '',
        status TEXT DEFAULT 'pending',
        response TEXT DEFAULT '',
        created_at TEXT DEFAULT ''
    )
    """)
    conn.commit()
    conn.close()

def record_conversion_event(user_id: int, event_type: str, source: str = "", message: str = "", metadata=None):
    ensure_conversion_tables()
    try:
        meta = json.dumps(metadata or {}, ensure_ascii=False)
    except Exception:
        meta = "{}"
    conn = db()
    conn.execute("INSERT INTO conversion_events (user_id, event_type, source, message, metadata, created_at) VALUES (?, ?, ?, ?, ?, ?)", (user_id, event_type, source, message, meta, now()))
    conn.commit()
    conn.close()

def telegram_ready():
    return bool(os.getenv("TELEGRAM_BOT_TOKEN"))

def telegram_api_url(method: str):
    return f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN','')}/{method}"

def send_telegram_message(user_id: int, message: str, event_type: str = "general"):
    ensure_conversion_tables()
    user = get_user(user_id)
    chat_id = user.get("telegram_chat_id", "")
    if not telegram_ready():
        return {"sent": False, "reason": "TELEGRAM_BOT_TOKEN missing"}
    if not chat_id:
        return {"sent": False, "reason": "telegram_chat_id not linked"}
    status = "failed"
    response_text = ""
    try:
        resp = requests.post(telegram_api_url("sendMessage"), json={"chat_id": chat_id, "text": message, "parse_mode": "HTML", "disable_web_page_preview": True}, timeout=12)
        response_text = resp.text[:500]
        status = "sent" if resp.status_code == 200 else "failed"
        return {"sent": resp.status_code == 200, "status_code": resp.status_code, "response": response_text}
    except Exception as e:
        response_text = str(e)[:500]
        return {"sent": False, "reason": response_text}
    finally:
        conn = db()
        conn.execute("INSERT INTO notification_logs (user_id, channel, event_type, message, status, response, created_at) VALUES (?, 'telegram', ?, ?, ?, ?, ?)", (user_id, event_type, message, status, response_text, now()))
        conn.commit()
        conn.close()

def build_daily_command_message(user_id: int):
    user = get_user(user_id)
    talent = calculate_talent_profile(user)
    target = int(user.get("goal_daily", 500) or 500)
    return f"""🔥 <b>Zero2Earn Daily Command</b>

Target: ₹{target}

1) Continue First ₹100 / Daily ₹500 action
2) Prepare 3 resume-matched jobs
3) Use Wingman for the strongest job
4) Track proof after every win
5) Send follow-ups after 3–5 days

Talent Score: {talent.get('talent_score', 0)}%
Open Zero2Earn and continue your mission."""

def build_upgrade_message(user_id: int):
    trigger = upgrade_trigger_for_user(user_id)
    msg = trigger.get("message") or "Unlock Pro to continue your earning workflow."
    return f"""🚀 <b>Zero2Earn Pro Unlock</b>

{msg}

Pro unlocks:
• Unlimited AI Wingman
• Daily ₹500 execution support
• Recruiter visibility boost
• Faster proposal + follow-up flow

Open Zero2Earn → Plans → Upgrade."""

def build_job_alert_message(user_id: int, job=None):
    job = job or {}
    return f"""💼 <b>New Job Match</b>

{job.get('title','New matched job')}
{job.get('company','Zero2Earn Jobs Engine')}
Match: {job.get('score','')}%

Open Zero2Earn → Earn Engine → Wingman → Apply.
{job.get('url','')}"""

def maybe_send_upgrade_nudge(user_id: int, source: str = "auto"):
    user = get_user(user_id)
    if is_pro_user(user):
        return {"sent": False, "reason": "already_pro"}
    trigger = upgrade_trigger_for_user(user_id)
    if not trigger.get("show"):
        return {"sent": False, "reason": "no_trigger"}
    result = send_telegram_message(user_id, build_upgrade_message(user_id), "upgrade_nudge")
    record_conversion_event(user_id, "upgrade_nudge", source, trigger.get("message", ""), {"telegram": result})
    return result

@app.get("/api/conversion/status/{user_id}")
def conversion_status(user_id: int):
    ensure_conversion_tables()
    user = get_user(user_id)
    return {
        "user_id": user_id,
        "plan": user.get("plan", "free"),
        "is_pro": is_pro_user(user),
        "ai_usage_today": ai_usage_today(user_id, "wingman"),
        "free_ai_limit": free_ai_limit(),
        "upgrade_trigger": upgrade_trigger_for_user(user_id),
        "sticky_cta": not is_pro_user(user),
        "daily500_locked": not is_pro_user(user),
        "telegram": {
            "bot_configured": telegram_ready(),
            "linked": bool(user.get("telegram_chat_id", "")),
            "chat_id": user.get("telegram_chat_id", "")
        }
    }

@app.get("/api/telegram/status/{user_id}")
def telegram_status(user_id: int):
    ensure_conversion_tables()
    user = get_user(user_id)
    return {"bot_configured": telegram_ready(), "linked": bool(user.get("telegram_chat_id","")), "chat_id": user.get("telegram_chat_id",""), "username": user.get("telegram_username",""), "notification_opt_in": int(user.get("notification_opt_in") or 1)}

@app.post("/api/telegram/link/{user_id}")
def telegram_link(user_id: int, chat_id: str = Form(...), username: str = Form("")):
    ensure_conversion_tables()
    get_user(user_id)
    conn = db()
    conn.execute("UPDATE users SET telegram_chat_id=?, telegram_username=?, notification_opt_in=1 WHERE id=?", (chat_id.strip(), username.strip(), user_id))
    conn.commit()
    conn.close()
    result = send_telegram_message(user_id, "✅ Zero2Earn Telegram alerts connected. Daily command, job alerts and recruiter alerts are ready.", "telegram_linked")
    return {"status": "linked", "chat_id": chat_id, "telegram": result}

@app.post("/api/telegram/unlink/{user_id}")
def telegram_unlink(user_id: int):
    ensure_conversion_tables()
    get_user(user_id)
    conn = db()
    conn.execute("UPDATE users SET telegram_chat_id='', telegram_username='' WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return {"status": "unlinked"}

@app.post("/api/telegram/test/{user_id}")
def telegram_test(user_id: int):
    return send_telegram_message(user_id, "🔥 Zero2Earn test alert working. Your command system is connected.", "test")

@app.get("/api/telegram/get-updates")
def telegram_get_updates():
    if not telegram_ready():
        raise HTTPException(status_code=500, detail="TELEGRAM_BOT_TOKEN missing")
    try:
        resp = requests.get(telegram_api_url("getUpdates"), timeout=12)
        return resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/telegram/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    message = data.get("message", {})
    chat = message.get("chat", {})
    text = (message.get("text") or "").strip()
    chat_id = str(chat.get("id", ""))
    username = chat.get("username", "")
    reply = ""
    if text.startswith("/start"):
        reply = "🔥 Welcome to Zero2Earn alerts.\n\nYour chat ID:\n" + chat_id + "\n\nPaste this in Zero2Earn → Plans → Telegram Alerts."
    elif text.startswith("/id"):
        reply = "Your chat ID: " + chat_id
    elif text.startswith("/daily"):
        reply = "Open Zero2Earn and continue your Daily Command."
    if reply and telegram_ready() and chat_id:
        requests.post(telegram_api_url("sendMessage"), json={"chat_id": chat_id, "text": reply}, timeout=12)
    return {"status": "ok", "chat_id": chat_id, "username": username}

@app.post("/api/notifications/daily-command/{user_id}")
def notify_daily_command(user_id: int):
    result = send_telegram_message(user_id, build_daily_command_message(user_id), "daily_command")
    conn = db()
    conn.execute("UPDATE users SET last_daily_alert_at=? WHERE id=?", (now(), user_id))
    conn.commit()
    conn.close()
    record_conversion_event(user_id, "daily_command_sent", "telegram", "Daily command alert sent", result)
    return result

@app.post("/api/notifications/job-alert/{user_id}")
def notify_job_alert(user_id: int):
    jobs = build_job_cards(get_user(user_id))
    top = jobs[0] if jobs else {}
    result = send_telegram_message(user_id, build_job_alert_message(user_id, top), "job_alert")
    record_conversion_event(user_id, "job_alert_sent", "telegram", top.get("title", ""), top)
    return {"job": top, "telegram": result}

@app.post("/api/notifications/recruiter-alert/{user_id}")
def notify_recruiter_alert(user_id: int, role: str = Form("Recruiter opportunity"), company: str = Form("Company")):
    msg = f"🏢 <b>Recruiter Alert</b>\n\n{company} showed interest in:\n{role}\n\nOpen Zero2Earn → Recruiter / Talent Pool."
    result = send_telegram_message(user_id, msg, "recruiter_alert")
    record_conversion_event(user_id, "recruiter_alert_sent", "telegram", role, {"company": company})
    return result

@app.post("/api/conversion/nudge/{user_id}")
def conversion_nudge(user_id: int, source: str = Form("manual")):
    return maybe_send_upgrade_nudge(user_id, source)

@app.get("/api/conversion/events/{user_id}")
def conversion_events(user_id: int):
    ensure_conversion_tables()
    conn = db()
    rows = rows_to_dicts(conn.execute("SELECT * FROM conversion_events WHERE user_id=? ORDER BY id DESC LIMIT 50", (user_id,)).fetchall())
    conn.close()
    return {"items": rows}




# ---------------- TELEGRAM CONNECT UX ENDPOINTS ----------------

@app.get("/api/telegram/connect-guide/{user_id}")
def telegram_connect_guide(user_id: int):
    user = get_user(user_id)
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    bot_configured = bool(bot_token)
    bot_username = os.getenv("TELEGRAM_BOT_USERNAME", "")
    return {
        "bot_configured": bot_configured,
        "linked": bool(user.get("telegram_chat_id", "")),
        "chat_id": user.get("telegram_chat_id", ""),
        "username": user.get("telegram_username", ""),
        "bot_username": bot_username,
        "steps": [
            "Open Telegram and search your Zero2Earn bot.",
            "Press Start or send /start.",
            "Send /id or any message like hello.",
            "Return to Zero2Earn and click Detect Chat ID.",
            "Click Connect Telegram.",
            "Click Send Test Alert."
        ],
        "manual_api": "/api/telegram/get-updates",
        "note": "Telegram must receive at least one message from the user before chat ID can be detected."
    }


@app.get("/api/telegram/detect-chat")
def telegram_detect_chat():
    if not telegram_ready():
        raise HTTPException(status_code=500, detail="TELEGRAM_BOT_TOKEN missing")
    try:
        resp = requests.get(telegram_api_url("getUpdates"), timeout=12)
        data = resp.json()
        chats = []
        for item in data.get("result", []):
            msg = item.get("message", {}) or item.get("edited_message", {})
            chat = msg.get("chat", {})
            if chat.get("id"):
                chats.append({
                    "chat_id": str(chat.get("id")),
                    "first_name": chat.get("first_name", ""),
                    "last_name": chat.get("last_name", ""),
                    "username": chat.get("username", ""),
                    "type": chat.get("type", ""),
                    "text": msg.get("text", "")
                })
        # de-duplicate, latest first
        seen = set()
        unique = []
        for c in reversed(chats):
            if c["chat_id"] not in seen:
                unique.append(c)
                seen.add(c["chat_id"])
        return {"count": len(unique), "items": unique[:10]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/telegram/opt-in/{user_id}")
def telegram_opt_in(user_id: int, enabled: int = Form(1)):
    ensure_conversion_tables()
    get_user(user_id)
    conn = db()
    conn.execute("UPDATE users SET notification_opt_in=? WHERE id=?", (1 if int(enabled or 0) else 0, user_id))
    conn.commit()
    conn.close()
    return {"status": "updated", "notification_opt_in": 1 if int(enabled or 0) else 0}




# ---------------- TELEGRAM ENGINE FULL ----------------

def ensure_telegram_engine_tables():
    conn = db()
    cur = conn.cursor()
    for col, definition in {
        "telegram_chat_id": "TEXT DEFAULT ''",
        "telegram_username": "TEXT DEFAULT ''",
        "notification_opt_in": "INTEGER DEFAULT 1",
        "last_daily_alert_at": "TEXT DEFAULT ''",
        "last_job_alert_at": "TEXT DEFAULT ''",
        "last_recruiter_alert_at": "TEXT DEFAULT ''",
        "last_upgrade_nudge_at": "TEXT DEFAULT ''"
    }.items():
        try:
            add_column(cur, "users", col, definition)
        except Exception:
            pass
    cur.execute("""
    CREATE TABLE IF NOT EXISTS telegram_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        event_type TEXT DEFAULT '',
        message TEXT DEFAULT '',
        status TEXT DEFAULT '',
        response TEXT DEFAULT '',
        created_at TEXT DEFAULT ''
    )
    """)
    conn.commit()
    conn.close()

def telegram_ready():
    return bool(os.getenv("TELEGRAM_BOT_TOKEN"))

def telegram_api_url(method: str):
    return f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN','')}/{method}"

def telegram_send_raw(chat_id: str, message: str):
    if not telegram_ready():
        return {"sent": False, "reason": "TELEGRAM_BOT_TOKEN missing"}
    if not chat_id:
        return {"sent": False, "reason": "chat_id missing"}
    try:
        resp = requests.post(telegram_api_url("sendMessage"), json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }, timeout=12)
        return {"sent": resp.status_code == 200, "status_code": resp.status_code, "response": resp.text[:700]}
    except Exception as e:
        return {"sent": False, "reason": str(e)[:700]}

def telegram_log(user_id: int, event_type: str, message: str, result: dict):
    ensure_telegram_engine_tables()
    conn = db()
    conn.execute("""
    INSERT INTO telegram_events (user_id, event_type, message, status, response, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, event_type, message, "sent" if result.get("sent") else "failed", json.dumps(result, ensure_ascii=False)[:900], now()))
    conn.commit()
    conn.close()

def telegram_send_user(user_id: int, message: str, event_type: str = "general"):
    ensure_telegram_engine_tables()
    user = get_user(user_id)
    if int(user.get("notification_opt_in") or 1) != 1:
        result = {"sent": False, "reason": "user opted out"}
        telegram_log(user_id, event_type, message, result)
        return result
    result = telegram_send_raw(user.get("telegram_chat_id", ""), message)
    telegram_log(user_id, event_type, message, result)
    return result

def telegram_daily_message(user_id: int):
    user = get_user(user_id)
    target = int(user.get("goal_daily", 500) or 500)
    name = user.get("name") or "Zero2Earn user"
    return f"""🔥 <b>Zero2Earn Daily Command</b>

Hi {name},
Today’s target: <b>₹{target}</b>

1) Complete 1 micro-income action
2) Prepare 1 job with Wingman
3) Apply and mark tracked
4) Add proof or progress

Open Zero2Earn and continue now."""

def telegram_job_message(user_id: int):
    user = get_user(user_id)
    try:
        jobs = build_job_cards(user)
        job = jobs[0] if jobs else {}
    except Exception:
        job = {}
    return f"""💼 <b>New Job Match</b>

<b>{job.get('title','New matched job')}</b>
{job.get('company','Zero2Earn Jobs Engine')}
Match score: {job.get('score','')}%

Open Zero2Earn → Jobs Engine → Wingman."""

def telegram_recruiter_message(user_id: int, company: str = "Recruiter", role: str = "your profile"):
    return f"""🏢 <b>Recruiter Alert</b>

{company} activity for:
<b>{role}</b>

Open Zero2Earn → Talent Pool / Recruiter Hiring."""

def telegram_upgrade_message(user_id: int):
    try:
        trigger = upgrade_trigger_for_user(user_id)
        msg = trigger.get("message", "Unlock Pro to continue your earning workflow.")
    except Exception:
        msg = "Unlock Pro to continue your earning workflow."
    return f"""🚀 <b>Zero2Earn Pro</b>

{msg}

Pro unlocks:
• Unlimited AI Wingman
• Daily ₹500 execution
• Recruiter visibility boost
• Telegram retention alerts

Open Plans → Upgrade ₹299."""

@app.get("/api/telegram/engine/status/{user_id}")
def telegram_engine_status(user_id: int):
    ensure_telegram_engine_tables()
    user = get_user(user_id)
    conn = db()
    events = rows_to_dicts(conn.execute("SELECT * FROM telegram_events WHERE user_id=? ORDER BY id DESC LIMIT 10", (user_id,)).fetchall())
    conn.close()
    return {
        "bot_configured": telegram_ready(),
        "linked": bool(user.get("telegram_chat_id","")),
        "chat_id": user.get("telegram_chat_id",""),
        "username": user.get("telegram_username",""),
        "notification_opt_in": int(user.get("notification_opt_in") or 1),
        "recent_events": events
    }

@app.get("/api/telegram/detect-chat")
def telegram_detect_chat():
    if not telegram_ready():
        raise HTTPException(status_code=500, detail="TELEGRAM_BOT_TOKEN missing")
    resp = requests.get(telegram_api_url("getUpdates"), timeout=12)
    data = resp.json()
    chats = []
    for item in data.get("result", []):
        msg = item.get("message", {}) or item.get("edited_message", {})
        chat = msg.get("chat", {})
        if chat.get("id"):
            chats.append({
                "chat_id": str(chat.get("id")),
                "first_name": chat.get("first_name",""),
                "last_name": chat.get("last_name",""),
                "username": chat.get("username",""),
                "text": msg.get("text","")
            })
    seen=set(); unique=[]
    for c in reversed(chats):
        if c["chat_id"] not in seen:
            unique.append(c); seen.add(c["chat_id"])
    return {"count": len(unique), "items": unique[:10], "raw_ok": data.get("ok", False)}

@app.post("/api/telegram/link/{user_id}")
def telegram_link_user(user_id: int, chat_id: str = Form(...), username: str = Form("")):
    ensure_telegram_engine_tables()
    get_user(user_id)
    conn = db()
    conn.execute("UPDATE users SET telegram_chat_id=?, telegram_username=?, notification_opt_in=1 WHERE id=?", (chat_id.strip(), username.strip(), user_id))
    conn.commit(); conn.close()
    result = telegram_send_user(user_id, "✅ Zero2Earn Telegram connected. Daily command, job alerts and recruiter alerts are active.", "telegram_linked")
    return {"status": "linked", "chat_id": chat_id, "telegram": result}

@app.post("/api/telegram/test/{user_id}")
def telegram_test_user(user_id: int):
    return telegram_send_user(user_id, "🔥 Zero2Earn test alert working. Telegram Engine is live.", "test")

@app.post("/api/telegram/send/daily/{user_id}")
def telegram_send_daily(user_id: int):
    result = telegram_send_user(user_id, telegram_daily_message(user_id), "daily_command")
    conn=db(); conn.execute("UPDATE users SET last_daily_alert_at=? WHERE id=?", (now(), user_id)); conn.commit(); conn.close()
    return result

@app.post("/api/telegram/send/job/{user_id}")
def telegram_send_job(user_id: int):
    result = telegram_send_user(user_id, telegram_job_message(user_id), "job_alert")
    conn=db(); conn.execute("UPDATE users SET last_job_alert_at=? WHERE id=?", (now(), user_id)); conn.commit(); conn.close()
    return result

@app.post("/api/telegram/send/recruiter/{user_id}")
def telegram_send_recruiter(user_id: int, company: str = Form("Recruiter"), role: str = Form("your profile")):
    result = telegram_send_user(user_id, telegram_recruiter_message(user_id, company, role), "recruiter_alert")
    conn=db(); conn.execute("UPDATE users SET last_recruiter_alert_at=? WHERE id=?", (now(), user_id)); conn.commit(); conn.close()
    return result

@app.post("/api/telegram/send/upgrade/{user_id}")
def telegram_send_upgrade(user_id: int):
    result = telegram_send_user(user_id, telegram_upgrade_message(user_id), "upgrade_nudge")
    conn=db(); conn.execute("UPDATE users SET last_upgrade_nudge_at=? WHERE id=?", (now(), user_id)); conn.commit(); conn.close()
    return result

@app.get("/api/telegram/events/{user_id}")
def telegram_events_user(user_id: int):
    ensure_telegram_engine_tables()
    conn=db()
    events=rows_to_dicts(conn.execute("SELECT * FROM telegram_events WHERE user_id=? ORDER BY id DESC LIMIT 50", (user_id,)).fetchall())
    conn.close()
    return {"items": events}




# ---------------- TELEGRAM INTELLIGENCE ENGINE ----------------

def ensure_telegram_intelligence_tables():
    ensure_telegram_engine_tables()
    conn = db()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS telegram_intelligence_state (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        last_smart_daily_at TEXT DEFAULT '',
        last_smart_job_at TEXT DEFAULT '',
        last_smart_upgrade_at TEXT DEFAULT '',
        last_smart_inactivity_at TEXT DEFAULT '',
        last_any_smart_alert_at TEXT DEFAULT '',
        quiet_until TEXT DEFAULT '',
        created_at TEXT DEFAULT ''
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS telegram_smart_decisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        decision_type TEXT DEFAULT '',
        decision TEXT DEFAULT '',
        reason TEXT DEFAULT '',
        score INTEGER DEFAULT 0,
        message TEXT DEFAULT '',
        sent INTEGER DEFAULT 0,
        created_at TEXT DEFAULT ''
    )
    """)
    conn.commit()
    conn.close()

def tg_parse_dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None

def tg_hours_since(value):
    dt = tg_parse_dt(value)
    if not dt:
        return 9999
    return (datetime.now() - dt).total_seconds() / 3600

def telegram_get_intel_state(user_id: int):
    ensure_telegram_intelligence_tables()
    conn = db()
    row = conn.execute("SELECT * FROM telegram_intelligence_state WHERE user_id=?", (user_id,)).fetchone()
    if not row:
        conn.execute("""
        INSERT INTO telegram_intelligence_state (user_id, created_at)
        VALUES (?, ?)
        """, (user_id, now()))
        conn.commit()
        row = conn.execute("SELECT * FROM telegram_intelligence_state WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return dict(row)

def telegram_set_intel_state(user_id: int, field: str):
    allowed = {
        "last_smart_daily_at",
        "last_smart_job_at",
        "last_smart_upgrade_at",
        "last_smart_inactivity_at",
        "last_any_smart_alert_at"
    }
    if field not in allowed:
        return
    ensure_telegram_intelligence_tables()
    conn = db()
    conn.execute(f"UPDATE telegram_intelligence_state SET {field}=?, last_any_smart_alert_at=? WHERE user_id=?", (now(), now(), user_id))
    conn.commit()
    conn.close()

def telegram_log_decision(user_id: int, decision_type: str, decision: str, reason: str, score: int, message: str, sent: bool):
    ensure_telegram_intelligence_tables()
    conn = db()
    conn.execute("""
    INSERT INTO telegram_smart_decisions (user_id, decision_type, decision, reason, score, message, sent, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, decision_type, decision, reason, int(score), message, 1 if sent else 0, now()))
    conn.commit()
    conn.close()

def telegram_user_activity_snapshot(user_id: int):
    user = get_user(user_id)
    try:
        dash = dashboard(user_id)
    except Exception:
        dash = {}
    metrics = dash.get("metrics", {}) if isinstance(dash, dict) else {}
    tracking = dash.get("tracking", {}) if isinstance(dash, dict) else {}
    try:
        first100 = calculate_first100_summary(user_id)
    except Exception:
        first100 = {}
    try:
        billing = billing_status(user_id)
    except Exception:
        billing = {"is_pro": is_pro_user(user)}
    try:
        ai_used = ai_usage_today(user_id, "wingman")
    except Exception:
        ai_used = 0
    return {
        "user": user,
        "metrics": metrics,
        "tracking": tracking,
        "first100": first100,
        "billing": billing,
        "ai_used": ai_used,
        "is_pro": bool(billing.get("is_pro")),
        "goal": int(user.get("goal_daily", 500) or 500),
        "name": user.get("name") or "Zero2Earn user",
        "pending_tasks": int(metrics.get("pending_tasks", 0) or 0),
        "done_tasks": int(metrics.get("done_tasks", 0) or 0),
        "applications": int(metrics.get("jobs_applied", 0) or 0),
        "earned": int(metrics.get("total_earned", 0) or 0),
        "first100_progress": int(first100.get("progress_percent", 0) or 0),
        "first100_completed": bool(first100.get("completed", False)),
        "next_action": first100.get("next_action", "Open First ₹100 Mission")
    }

def telegram_should_send(user_id: int, decision_type: str):
    state = telegram_get_intel_state(user_id)
    quiet_until = tg_parse_dt(state.get("quiet_until"))
    if quiet_until and quiet_until > datetime.now():
        return False, "quiet_mode_active"

    # Global anti-spam: no more than 1 smart alert every 3 hours.
    if tg_hours_since(state.get("last_any_smart_alert_at")) < 3:
        return False, "global_cooldown"

    cooldowns = {
        "daily": ("last_smart_daily_at", 10),
        "job": ("last_smart_job_at", 8),
        "upgrade": ("last_smart_upgrade_at", 18),
        "inactivity": ("last_smart_inactivity_at", 12),
    }
    field, hours = cooldowns.get(decision_type, ("last_any_smart_alert_at", 6))
    if tg_hours_since(state.get(field)) < hours:
        return False, f"{decision_type}_cooldown"
    return True, "ok"

def telegram_build_smart_message(user_id: int, kind: str):
    snap = telegram_user_activity_snapshot(user_id)
    name = snap["name"]
    target = snap["goal"]
    next_action = snap["next_action"]
    progress = snap["first100_progress"]
    is_pro = snap["is_pro"]
    ai_used = snap["ai_used"]

    if kind == "daily":
        if snap["first100_completed"]:
            return f"""🔥 <b>{name}, today’s ₹{target} command is ready</b>

You already started the system.
Do this now:
1) Prepare 1 strong job with Wingman
2) Apply on official portal
3) Track proof or follow-up

Your next action: <b>{next_action}</b>"""
        return f"""🔥 <b>{name}, start your First ₹100 Mission</b>

Progress: <b>{progress}%</b>
Next action: <b>{next_action}</b>

Do only one small step now.
Avoid scams. Never pay to apply."""

    if kind == "job":
        try:
            user = get_user(user_id)
            jobs = build_job_cards(user)
            job = jobs[0] if jobs else {}
        except Exception:
            job = {}
        return f"""💼 <b>Smart Job Alert</b>

Best next match:
<b>{job.get('title','Resume-matched opportunity')}</b>
{job.get('company','Zero2Earn Jobs Engine')}
Score: {job.get('score','')}%

Open Zero2Earn → Jobs → Wingman.
Prepare before applying."""

    if kind == "upgrade":
        if is_pro:
            return ""
        if ai_used >= max(1, free_ai_limit() - 1):
            reason = "You are near your free AI Wingman limit."
        elif snap["first100_progress"] >= 60:
            reason = "You are close to first proof. Pro helps scale to Daily ₹500."
        else:
            reason = "Pro unlocks faster execution."
        return f"""🚀 <b>Scale Zero2Earn with Pro</b>

{reason}

Unlock:
• Unlimited AI Wingman
• Daily ₹500 Mode
• Recruiter visibility
• Stronger follow-up flow

₹299/month = about ₹10/day."""

    if kind == "inactivity":
        return f"""⚡ <b>Your Zero2Earn streak is waiting</b>

You don’t need to finish everything.
Just complete <b>one</b> action:

Next action: <b>{next_action}</b>

Open Zero2Earn and protect momentum."""

    return ""

def telegram_smart_decide(user_id: int):
    snap = telegram_user_activity_snapshot(user_id)
    decisions = []

    # Daily score
    daily_score = 50
    if snap["pending_tasks"] > 0:
        daily_score += 20
    if snap["first100_progress"] < 100:
        daily_score += 20
    decisions.append(("daily", daily_score, "daily command keeps retention"))

    # Job score
    job_score = 35
    if snap["applications"] == 0:
        job_score += 25
    if snap["first100_progress"] >= 20:
        job_score += 10
    decisions.append(("job", job_score, "job alert supports apply behavior"))

    # Upgrade score
    upgrade_score = 0
    if not snap["is_pro"]:
        upgrade_score = 40
        if snap["ai_used"] >= max(1, free_ai_limit() - 1):
            upgrade_score += 30
        if snap["first100_progress"] >= 60:
            upgrade_score += 25
    decisions.append(("upgrade", upgrade_score, "upgrade shown only after value signal"))

    # Inactivity score: simple proxy based on pending tasks/done zero
    inactivity_score = 30
    if snap["done_tasks"] == 0 and snap["pending_tasks"] > 0:
        inactivity_score += 35
    decisions.append(("inactivity", inactivity_score, "streak protection"))

    decisions = sorted(decisions, key=lambda x: x[1], reverse=True)
    for kind, score, reason in decisions:
        ok, gate = telegram_should_send(user_id, kind)
        if ok and score >= 50:
            msg = telegram_build_smart_message(user_id, kind)
            return {"decision": "send", "kind": kind, "score": score, "reason": reason, "message": msg}
        else:
            telegram_log_decision(user_id, kind, "skip", gate, score, "", False)

    return {"decision": "skip", "kind": "none", "score": 0, "reason": "no eligible smart alert", "message": ""}

@app.get("/api/telegram/intelligence/status/{user_id}")
def telegram_intelligence_status(user_id: int):
    ensure_telegram_intelligence_tables()
    state = telegram_get_intel_state(user_id)
    snap = telegram_user_activity_snapshot(user_id)
    decision = telegram_smart_decide(user_id)
    conn = db()
    recent = rows_to_dicts(conn.execute("""
    SELECT * FROM telegram_smart_decisions WHERE user_id=? ORDER BY id DESC LIMIT 15
    """, (user_id,)).fetchall())
    conn.close()
    return {
        "state": state,
        "snapshot": snap,
        "next_decision": decision,
        "recent_decisions": recent
    }

@app.post("/api/telegram/intelligence/run/{user_id}")
def telegram_intelligence_run(user_id: int):
    ensure_telegram_intelligence_tables()
    user = get_user(user_id)
    if not user.get("telegram_chat_id"):
        return {"sent": False, "reason": "telegram_not_linked"}
    decision = telegram_smart_decide(user_id)
    if decision["decision"] != "send":
        return {"sent": False, "decision": decision}
    result = telegram_send_user(user_id, decision["message"], "smart_" + decision["kind"])
    if result.get("sent"):
        field_map = {
            "daily": "last_smart_daily_at",
            "job": "last_smart_job_at",
            "upgrade": "last_smart_upgrade_at",
            "inactivity": "last_smart_inactivity_at",
        }
        telegram_set_intel_state(user_id, field_map.get(decision["kind"], "last_any_smart_alert_at"))
    telegram_log_decision(user_id, decision["kind"], "send", decision["reason"], decision["score"], decision["message"], bool(result.get("sent")))
    return {"sent": bool(result.get("sent")), "decision": decision, "telegram": result}

@app.post("/api/telegram/intelligence/run-all")
def telegram_intelligence_run_all(admin_key: str = Form("")):
    expected = os.getenv("ZERO2EARN_ADMIN_KEY", "")
    if expected and admin_key != expected:
        raise HTTPException(status_code=403, detail="Invalid admin key")
    ensure_telegram_intelligence_tables()
    conn = db()
    users = rows_to_dicts(conn.execute("""
    SELECT id FROM users WHERE telegram_chat_id!='' AND notification_opt_in=1
    """).fetchall())
    conn.close()
    items = []
    for u in users:
        try:
            items.append({"user_id": u["id"], "result": telegram_intelligence_run(u["id"])})
        except Exception as e:
            items.append({"user_id": u["id"], "error": str(e)})
    return {"count": len(items), "items": items}

@app.post("/api/telegram/intelligence/quiet/{user_id}")
def telegram_intelligence_quiet(user_id: int, hours: int = Form(24)):
    ensure_telegram_intelligence_tables()
    until = (datetime.now() + timedelta(hours=int(hours or 24))).isoformat(timespec="seconds")
    telegram_get_intel_state(user_id)
    conn = db()
    conn.execute("UPDATE telegram_intelligence_state SET quiet_until=? WHERE user_id=?", (until, user_id))
    conn.commit()
    conn.close()
    return {"status": "quiet_enabled", "quiet_until": until}
