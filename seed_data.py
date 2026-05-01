from pathlib import Path
import sqlite3

try:
    from zero2earn_backend.db import init_db, seed_demo
except Exception:
    init_db = None
    seed_demo = None

DB_PATH = Path("zero2earn.db")

def has_real_users():
    if not DB_PATH.exists():
        return False
    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute("SELECT COUNT(*) FROM users WHERE lower(email) != 'demo@zero2earn.ai'").fetchone()
        return int(row[0] or 0) > 0
    except Exception:
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    if init_db:
        init_db()
    if has_real_users():
        print("Real users found. Skipping demo seed to protect user data.")
    else:
        if seed_demo:
            seed_demo()
            print("Demo seed complete.")
        else:
            print("No seed_demo function found. Database initialized only.")
    print("Safe seed complete.")
