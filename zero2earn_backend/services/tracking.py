from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta

from ..db import get_cursor

ORDER = ['prepared', 'applied', 'viewed', 'replied', 'interview', 'hired', 'rejected']
GOOD = {'replied', 'interview', 'hired'}
ACTIVE = {'prepared', 'applied', 'viewed', 'replied', 'interview'}


def _now() -> str:
    return datetime.now().isoformat(timespec='seconds')


def _follow_up() -> str:
    return (datetime.now() + timedelta(days=3)).date().isoformat()


def ensure_tracking_columns() -> None:
    """SQLite-safe migration for existing user DBs."""
    columns = {
        'response_date': "ALTER TABLE applications ADD COLUMN response_date TEXT DEFAULT ''",
        'follow_up_date': "ALTER TABLE applications ADD COLUMN follow_up_date TEXT DEFAULT ''",
        'rejection_reason': "ALTER TABLE applications ADD COLUMN rejection_reason TEXT DEFAULT ''",
        'notes': "ALTER TABLE applications ADD COLUMN notes TEXT DEFAULT ''",
        'updated_at': "ALTER TABLE applications ADD COLUMN updated_at TEXT DEFAULT ''",
    }
    with get_cursor() as cur:
        existing = {row['name'] for row in cur.execute('PRAGMA table_info(applications)').fetchall()}
        for name, sql in columns.items():
            if name not in existing:
                cur.execute(sql)


def tracking_metrics(user_id: int) -> dict:
    ensure_tracking_columns()
    with get_cursor() as cur:
        rows = [dict(r) for r in cur.execute('SELECT * FROM applications WHERE user_id = ?', (user_id,)).fetchall()]

    counts = Counter((r.get('status') or 'applied') for r in rows)
    total = len(rows)
    applied_like = sum(counts[s] for s in ['applied', 'viewed', 'replied', 'interview', 'hired', 'rejected'])
    replies = counts['replied'] + counts['interview'] + counts['hired']
    interviews = counts['interview'] + counts['hired']
    hired = counts['hired']
    rejected = counts['rejected']
    prepared = counts['prepared']

    reply_rate = round((replies / applied_like) * 100, 1) if applied_like else 0
    interview_rate = round((interviews / applied_like) * 100, 1) if applied_like else 0
    hire_rate = round((hired / applied_like) * 100, 1) if applied_like else 0
    rejection_rate = round((rejected / applied_like) * 100, 1) if applied_like else 0

    avg_score = round(sum(int(r.get('score') or 0) for r in rows) / total, 1) if total else 0

    insights = []
    if prepared > 0:
        insights.append(f'{prepared} prepared applications are waiting. Open portals and submit them today.')
    if applied_like >= 10 and reply_rate < 8:
        insights.append('Reply rate is low. Use more specific first lines and apply to higher-score jobs first.')
    elif applied_like >= 5 and reply_rate >= 12:
        insights.append('Your reply rate is promising. Reuse the structure of proposals that received replies.')
    if avg_score and avg_score < 55:
        insights.append('Average application score is low. Use Skills tab before applying heavily.')
    if counts['viewed'] > 0 and replies == 0:
        insights.append('Employers are viewing but not replying. Improve proof lines and role-specific examples.')
    if not insights:
        insights.append('Start by preparing 10 high-score applications, submitting 5 today, and tracking every response.')

    return {
        'total': total,
        'prepared': prepared,
        'applied': counts['applied'],
        'viewed': counts['viewed'],
        'replied': counts['replied'],
        'interview': counts['interview'],
        'hired': hired,
        'rejected': rejected,
        'reply_rate': reply_rate,
        'interview_rate': interview_rate,
        'hire_rate': hire_rate,
        'rejection_rate': rejection_rate,
        'avg_score': avg_score,
        'insights': insights,
    }


def update_application_status(user_id: int, app_id: int, status: str, notes: str = '', rejection_reason: str = '') -> dict:
    ensure_tracking_columns()
    status = (status or '').strip().lower()
    if status not in ORDER:
        raise ValueError('Invalid status')
    now = _now()
    response_date = now if status in ['replied', 'interview', 'hired', 'rejected'] else ''
    follow_up = _follow_up() if status in ['applied', 'viewed'] else ''
    with get_cursor() as cur:
        row = cur.execute('SELECT * FROM applications WHERE id = ? AND user_id = ?', (app_id, user_id)).fetchone()
        if not row:
            raise LookupError('Application not found')
        cur.execute(
            '''UPDATE applications
               SET status = ?, notes = COALESCE(NULLIF(?, ''), notes), rejection_reason = COALESCE(NULLIF(?, ''), rejection_reason),
                   response_date = CASE WHEN ? != '' THEN ? ELSE response_date END,
                   follow_up_date = ?, updated_at = ?
               WHERE id = ? AND user_id = ?''',
            (status, notes, rejection_reason, response_date, response_date, follow_up, now, app_id, user_id),
        )
        cur.execute(
            'INSERT INTO alerts (user_id, message, created_at) VALUES (?, ?, ?)',
            (user_id, f'Application status updated to {status}: {row["title"]}', now),
        )
    return {'ok': True, 'status': status}
