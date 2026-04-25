import sqlite3
from pathlib import Path

DB_PATH = Path("zero2earn.db")


def get_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # USERS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        password TEXT,
        name TEXT,
        headline TEXT,
        summary TEXT,
        track TEXT,
        stage TEXT,
        goal_daily INTEGER,
        plan TEXT DEFAULT 'free'
    )
    """)

    # TASKS (FULL FIXED STRUCTURE)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        task_type TEXT,
        title TEXT,
        description TEXT,
        estimated_reward INTEGER,
        priority INTEGER,
        status TEXT,
        linked_job_id TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # APPLICATIONS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        job_title TEXT,
        company TEXT,
        status TEXT,
        score INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # INCOME
    cur.execute("""
    CREATE TABLE IF NOT EXISTS income (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount INTEGER,
        source TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # LEADS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        org TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


def seed_demo():
    conn = get_conn()
    cur = conn.cursor()

    # RESET USERS
    cur.execute("DELETE FROM users")
    cur.execute("""
    INSERT INTO users (email, password, name, headline, summary, track, stage, goal_daily, plan)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "test@zero2earn.com",
        "1234",
        "Dr Ramesh",
        "Medical Writer | Clinical Research Specialist | Healthcare Consultant",
        "AI-powered medical career transition",
        "Medical + AI",
        "Zero",
        500,
        "pro"
    ))

    user_id = cur.lastrowid

    # RESET TASKS
    cur.execute("DELETE FROM tasks")

    tasks = [
        ("apply", "Submit 5 prepared applications", "Apply to jobs", 500, 10, "pending", None),
        ("track", "Update application statuses", "Track pipeline", 0, 9, "pending", None),
        ("micro", "Complete one microjob", "Earn fast", 100, 8, "pending", None),
        ("skill", "Fix one skill gap", "Improve profile", 0, 7, "pending", None)
    ]

    for t in tasks:
        cur.execute("""
        INSERT INTO tasks (
            user_id, task_type, title, description,
            estimated_reward, priority, status, linked_job_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, *t))

    conn.commit()
    conn.close()