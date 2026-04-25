from __future__ import annotations

from datetime import date

from ..db import get_cursor


def get_today_tasks(user_id: int) -> list[dict]:
    today = date.today().isoformat()
    with get_cursor() as cur:
        rows = cur.execute(
            '''SELECT id, task_type, title, description, estimated_reward, priority, status, linked_job_id
               FROM tasks WHERE user_id = ? AND task_date = ?
               ORDER BY priority DESC, id ASC''',
            (user_id, today),
        ).fetchall()
    return [dict(r) for r in rows]


def replace_today_tasks(user_id: int, tasks: list[dict]) -> None:
    today = date.today().isoformat()
    with get_cursor() as cur:
        cur.execute('DELETE FROM tasks WHERE user_id = ? AND task_date = ? AND status = ?', (user_id, today, 'pending'))
        for task in tasks:
            cur.execute(
                '''INSERT INTO tasks (user_id, task_date, task_type, title, description, estimated_reward, priority, linked_job_id, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')''',
                (
                    user_id,
                    today,
                    task.get('task_type', 'general'),
                    task.get('title', ''),
                    task.get('description', ''),
                    int(task.get('estimated_reward', 0) or 0),
                    int(task.get('priority', 0) or 0),
                    task.get('linked_job_id'),
                ),
            )


def complete_task(task_id: int) -> None:
    with get_cursor() as cur:
        cur.execute('UPDATE tasks SET status = ? WHERE id = ?', ('done', task_id))
