from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from ..db import get_cursor
from .wingman import wingman_payload
from .tracking import tracking_metrics


def _now() -> str:
    return datetime.now().isoformat(timespec='seconds')


def _today() -> str:
    return date.today().isoformat()


def _follow_up_date(days: int = 3) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


def _safe(value: Any, default: str = '') -> str:
    text = '' if value is None else str(value).strip()
    return text or default


def build_daily_automation_plan(user_id: int, user: dict, ranked_jobs: list[dict], limit: int = 20, min_score: int = 55) -> dict:
    metrics = tracking_metrics(user_id)
    candidates = [j for j in ranked_jobs if int(j.get('match_score') or 0) >= min_score]
    top_jobs = candidates[: max(1, min(int(limit or 20), 30))]
    high_score = [j for j in ranked_jobs if int(j.get('match_score') or 0) >= 75]
    followups = get_due_followups(user_id)
    forecast = income_forecast(user_id)
    streak = streak_status(user_id)

    commands = [
        f"Prepare {min(len(top_jobs), 20)} applications from high-fit jobs.",
        f"Submit {min(max(metrics.get('prepared', 0), 5), 10)} prepared applications today.",
        f"Send {len(followups)} follow-up messages due today." if followups else "Track all submitted applications and update statuses.",
        "Complete 1 microjob or 1 skill-gap task if job scores are weak.",
    ]

    return {
        'mode': 'Daily Mode ON',
        'recommended_queue_size': len(top_jobs),
        'high_score_jobs': len(high_score),
        'min_score': min_score,
        'commands': commands,
        'top_jobs': [
            {
                'id': j.get('id'),
                'title': j.get('title'),
                'company': j.get('company'),
                'source': j.get('source'),
                'score': j.get('match_score'),
                'win_probability': j.get('win_probability'),
                'apply_url': j.get('apply_url'),
            }
            for j in top_jobs[:10]
        ],
        'followups_due': followups,
        'forecast': forecast,
        'streak': streak,
        'metrics': metrics,
    }


def prepare_queue(user_id: int, user: dict, ranked_jobs: list[dict], limit: int = 10, min_score: int = 55) -> dict:
    selected = [j for j in ranked_jobs if int(j.get('match_score') or 0) >= int(min_score or 0)]
    selected = selected[: max(1, min(int(limit or 10), 25))]
    now = _now()
    prepared = []
    skipped = []

    with get_cursor() as cur:
        for job in selected:
            job_id = _safe(job.get('id'))
            existing = cur.execute(
                'SELECT id, status FROM applications WHERE user_id = ? AND job_id = ? LIMIT 1',
                (user_id, job_id),
            ).fetchone()
            if existing:
                skipped.append({'job_id': job_id, 'title': job.get('title'), 'status': existing['status']})
                continue
            w = wingman_payload(job, user)
            cur.execute(
                '''INSERT INTO applications
                   (user_id, job_id, title, company, source, apply_url, status, proposal, score, follow_up_date, updated_at, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, 'prepared', ?, ?, '', ?, ?)''',
                (
                    user_id,
                    job_id,
                    _safe(job.get('title'), 'Untitled role'),
                    _safe(job.get('company'), 'Unknown company'),
                    _safe(job.get('source'), 'Live'),
                    _safe(job.get('apply_url'), '#'),
                    w['proposal'],
                    int(job.get('match_score') or 0),
                    now,
                    now,
                ),
            )
            prepared.append({'job_id': job_id, 'title': job.get('title'), 'company': job.get('company'), 'score': job.get('match_score')})
        cur.execute(
            'INSERT INTO alerts (user_id, message, created_at) VALUES (?, ?, ?)',
            (user_id, f'Automation prepared {len(prepared)} applications. Skipped {len(skipped)} duplicates.', now),
        )
    return {'ok': True, 'prepared': prepared, 'skipped': skipped, 'count': len(prepared)}


def get_due_followups(user_id: int) -> list[dict]:
    today = _today()
    with get_cursor() as cur:
        rows = cur.execute(
            '''SELECT * FROM applications
               WHERE user_id = ?
                 AND status IN ('applied','viewed')
                 AND (follow_up_date <= ? OR follow_up_date = '')
               ORDER BY score DESC, id DESC
               LIMIT 20''',
            (user_id, today),
        ).fetchall()
    out = []
    for r in rows:
        app = dict(r)
        out.append({
            'id': app['id'],
            'title': app['title'],
            'company': app['company'],
            'apply_url': app['apply_url'],
            'status': app['status'],
            'follow_up_date': app.get('follow_up_date') or today,
            'message': followup_message(app),
        })
    return out


def followup_message(app: dict) -> str:
    title = _safe(app.get('title'), 'the role')
    company = _safe(app.get('company'), 'your team')
    return (
        f"Hi {company} team,\n\n"
        f"I wanted to briefly follow up on my application for {title}. "
        "I remain interested in the opportunity and would be happy to share any additional details that help your evaluation.\n\n"
        "Thank you for your time.\n\nBest regards"
    )


def mark_followup_sent(user_id: int, app_id: int) -> dict:
    now = _now()
    next_date = (date.today() + timedelta(days=7)).isoformat()
    with get_cursor() as cur:
        row = cur.execute('SELECT * FROM applications WHERE id = ? AND user_id = ?', (app_id, user_id)).fetchone()
        if not row:
            raise LookupError('Application not found')
        cur.execute(
            '''UPDATE applications
               SET notes = TRIM(COALESCE(notes, '') || '\nFollow-up sent: ' || ?), follow_up_date = ?, updated_at = ?
               WHERE id = ? AND user_id = ?''',
            (now, next_date, now, app_id, user_id),
        )
        cur.execute('INSERT INTO alerts (user_id, message, created_at) VALUES (?, ?, ?)', (user_id, f'Follow-up marked sent: {row["title"]}', now))
    return {'ok': True, 'next_follow_up_date': next_date}


def income_forecast(user_id: int) -> dict:
    metrics = tracking_metrics(user_id)
    with get_cursor() as cur:
        inc = cur.execute('SELECT COALESCE(SUM(amount), 0) AS total FROM income_entries WHERE user_id = ?', (user_id,)).fetchone()['total']
    applied_base = max(1, metrics.get('applied', 0) + metrics.get('viewed', 0) + metrics.get('replied', 0) + metrics.get('interview', 0) + metrics.get('hired', 0) + metrics.get('rejected', 0))
    reply_rate = float(metrics.get('reply_rate') or 0)
    interview_rate = float(metrics.get('interview_rate') or 0)
    quality = max(0.5, min(1.8, (reply_rate / 10.0) + (interview_rate / 18.0) + 0.5))
    projected_7d = int(500 * quality + metrics.get('prepared', 0) * 20)
    projected_30d = int(projected_7d * 4.2)
    return {
        'earned_total': int(inc or 0),
        'projected_7d': projected_7d,
        'projected_30d': projected_30d,
        'message': f"At your current conversion behavior, estimated opportunity momentum is ₹{projected_7d} in 7 days and ₹{projected_30d} in 30 days.",
    }


def streak_status(user_id: int) -> dict:
    with get_cursor() as cur:
        rows = cur.execute(
            '''SELECT substr(created_at,1,10) AS d, COUNT(*) AS c
               FROM applications
               WHERE user_id = ?
               GROUP BY substr(created_at,1,10)
               ORDER BY d DESC
               LIMIT 30''',
            (user_id,),
        ).fetchall()
    dates = {r['d'] for r in rows if r['d']}
    streak = 0
    cursor = date.today()
    while cursor.isoformat() in dates:
        streak += 1
        cursor -= timedelta(days=1)
    today_count = next((int(r['c']) for r in rows if r['d'] == _today()), 0)
    return {
        'streak_days': streak,
        'today_applications': today_count,
        'message': f"{streak}-day application streak. {today_count} applications prepared/submitted today.",
    }
