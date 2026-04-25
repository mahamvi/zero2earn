from __future__ import annotations

from datetime import datetime
from typing import Any

from ..db import get_cursor
from .tasks import replace_today_tasks, get_today_tasks

SKILL_LIBRARY: dict[str, dict[str, Any]] = {
    "sql": {
        "name": "SQL",
        "category": "Data / Analytics",
        "why": "SQL appears in many analyst, QA, operations, data and support roles. It improves filtering, reporting and database-readiness.",
        "time": "3–5 days basics",
        "resume_line": "Added SQL basics: SELECT, WHERE, JOIN, GROUP BY and simple reporting queries.",
        "resources": [
            {"title": "SQLBolt interactive SQL lessons", "url": "https://sqlbolt.com/"},
            {"title": "Mode SQL Tutorial", "url": "https://mode.com/sql-tutorial/"},
        ],
        "project": "Create a small job-tracker or income-tracker table and write 5 useful queries from it.",
    },
    "excel": {
        "name": "Excel",
        "category": "Office / Data",
        "why": "Excel is a fast employability multiplier for data entry, operations, admin, analyst and remote support roles.",
        "time": "2–4 days basics",
        "resume_line": "Added Excel basics: sorting, filters, formulas, pivot tables and clean reporting.",
        "resources": [
            {"title": "Microsoft Excel training", "url": "https://support.microsoft.com/en-us/excel"},
            {"title": "Excel Easy", "url": "https://www.excel-easy.com/"},
        ],
        "project": "Build a simple earning tracker with formulas, filters and one pivot table.",
    },
    "automation": {
        "name": "Automation",
        "category": "Productivity / Tech",
        "why": "Automation increases fit for QA, operations, workflow, AI assistant, data processing and productivity roles.",
        "time": "5–7 days basics",
        "resume_line": "Added workflow automation basics using structured checklists and simple no-code/AI-assisted processes.",
        "resources": [
            {"title": "Zapier Learn", "url": "https://zapier.com/learn"},
            {"title": "Make Academy", "url": "https://www.make.com/en/academy"},
        ],
        "project": "Create a workflow that turns a job listing into a saved application checklist and proposal draft.",
    },
    "api": {
        "name": "API basics",
        "category": "Tech",
        "why": "API understanding helps with QA, support, developer-adjacent, automation and AI workflow roles.",
        "time": "5–7 days basics",
        "resume_line": "Added API basics: requests, responses, JSON, endpoints and simple testing concepts.",
        "resources": [
            {"title": "Postman Student Program", "url": "https://www.postman.com/student-program/"},
            {"title": "MDN HTTP overview", "url": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Overview"},
        ],
        "project": "Test one public API in Postman and document request, response and error cases.",
    },
    "testing": {
        "name": "Software Testing",
        "category": "QA",
        "why": "Testing is useful for QA, support, product operations and remote tech-adjacent roles.",
        "time": "3–5 days basics",
        "resume_line": "Added manual testing basics: test cases, bug reports, regression checks and acceptance criteria.",
        "resources": [
            {"title": "Guru99 Software Testing", "url": "https://www.guru99.com/software-testing.html"},
            {"title": "Ministry of Testing resources", "url": "https://www.ministryoftesting.com/"},
        ],
        "project": "Write 10 test cases and 3 bug reports for any website or app you use daily.",
    },
    "communication": {
        "name": "Professional Communication",
        "category": "Soft Skill",
        "why": "Clear communication improves response rate for remote jobs, support, writing, operations and freelance work.",
        "time": "2–3 days practice",
        "resume_line": "Added professional communication: concise updates, client-facing messages and structured follow-ups.",
        "resources": [
            {"title": "Google Applied Digital Skills", "url": "https://applieddigitalskills.withgoogle.com/"},
            {"title": "Purdue OWL professional writing", "url": "https://owl.purdue.edu/"},
        ],
        "project": "Write 3 application messages: short pitch, follow-up and status update.",
    },
    "portfolio": {
        "name": "Portfolio",
        "category": "Proof of Work",
        "why": "A portfolio gives proof and increases trust, especially for beginners, freelancers and career switchers.",
        "time": "1–2 days starter portfolio",
        "resume_line": "Created a starter portfolio with 2–3 proof-of-work samples relevant to target roles.",
        "resources": [
            {"title": "GitHub Pages", "url": "https://pages.github.com/"},
            {"title": "Notion portfolio templates", "url": "https://www.notion.so/templates/category/portfolio"},
        ],
        "project": "Create a one-page portfolio with resume summary, 3 skills and 2 sample projects.",
    },
    "python": {
        "name": "Python Basics",
        "category": "Tech / Automation",
        "why": "Python helps with automation, data, AI-support, scraping-adjacent and analyst roles.",
        "time": "7–14 days basics",
        "resume_line": "Added Python basics: scripts, loops, files, CSV processing and simple automation.",
        "resources": [
            {"title": "Python official tutorial", "url": "https://docs.python.org/3/tutorial/"},
            {"title": "Automate the Boring Stuff", "url": "https://automatetheboringstuff.com/"},
        ],
        "project": "Build a small script that reads a CSV of jobs and ranks them by keyword match.",
    },
    "content writing": {
        "name": "Content Writing",
        "category": "Writing",
        "why": "Writing improves fit for content, research, documentation, AI trainer and freelance roles.",
        "time": "3–5 days practice",
        "resume_line": "Added content writing samples with clear structure, research and audience-focused explanations.",
        "resources": [
            {"title": "HubSpot content marketing resources", "url": "https://academy.hubspot.com/courses/content-marketing"},
            {"title": "Google Search Central SEO basics", "url": "https://developers.google.com/search/docs/fundamentals/seo-starter-guide"},
        ],
        "project": "Write 2 short samples: one explainer article and one job-specific sample pitch.",
    },
}

DEFAULT_GAPS = ["communication", "excel", "portfolio"]


def normalize_skill(skill: str) -> str:
    return skill.strip().lower()


def build_skill_plan(skill: str) -> dict:
    key = normalize_skill(skill)
    item = SKILL_LIBRARY.get(key)
    if not item:
        item = {
            "name": skill.title(),
            "category": "General",
            "why": f"{skill.title()} appears in target jobs and can improve matching after basic proof-of-work is added.",
            "time": "3–5 days basics",
            "resume_line": f"Added practical basics in {skill.title()} with one proof-of-work sample.",
            "resources": [
                {"title": f"Search free {skill} course", "url": f"https://www.youtube.com/results?search_query=free+{skill.replace(' ', '+')}+course"},
                {"title": f"Search {skill} beginner guide", "url": f"https://www.google.com/search?q={skill.replace(' ', '+')}+beginner+guide"},
            ],
            "project": f"Create one small practical sample that proves basic {skill.title()} ability.",
        }
    return {"id": key, **item}


def infer_missing_skills_from_jobs(jobs: list[dict], limit: int = 8) -> list[str]:
    counts: dict[str, int] = {}
    for job in jobs:
        for skill in job.get("missing_skills", []) or []:
            key = normalize_skill(skill)
            if not key:
                continue
            counts[key] = counts.get(key, 0) + 1
    ranked = sorted(counts, key=lambda k: counts[k], reverse=True)
    return ranked[:limit]


def user_skill_plans(user: dict, jobs: list[dict] | None = None) -> list[dict]:
    existing = {normalize_skill(s) for s in (user.get("skills", []) or [])}
    gaps = infer_missing_skills_from_jobs(jobs or [])
    if not gaps:
        gaps = [g for g in DEFAULT_GAPS if g not in existing]
    plans = []
    seen = set()
    for gap in gaps:
        key = normalize_skill(gap)
        if key in existing or key in seen:
            continue
        plan = build_skill_plan(gap)
        plan["impact"] = estimate_skill_impact(key, jobs or [])
        plans.append(plan)
        seen.add(key)
    return plans[:6]


def estimate_skill_impact(skill: str, jobs: list[dict]) -> dict:
    key = normalize_skill(skill)
    affected = []
    for job in jobs:
        missing = [normalize_skill(x) for x in (job.get("missing_skills", []) or [])]
        if key in missing:
            affected.append(job)
    if not affected:
        return {"jobs_unlocked": 0, "score_lift": 5, "message": "Can improve general readiness and proposal quality."}
    avg_score = sum(int(j.get("match_score", 0)) for j in affected) // max(len(affected), 1)
    lift = 6 if avg_score >= 70 else 10 if avg_score >= 50 else 14
    return {
        "jobs_unlocked": len(affected),
        "score_lift": lift,
        "message": f"Could improve {len(affected)} matched job(s) by roughly {lift} points after proof-of-work.",
    }


def add_skill_to_today(user_id: int, skill: str) -> None:
    plan = build_skill_plan(skill)
    existing = get_today_tasks(user_id)
    tasks = [
        {
            "task_type": t["task_type"],
            "title": t["title"],
            "description": t["description"],
            "estimated_reward": t["estimated_reward"],
            "priority": t["priority"],
            "linked_job_id": t.get("linked_job_id"),
        }
        for t in existing if t.get("status") != "done"
    ]
    tasks.insert(0, {
        "task_type": "skill",
        "title": f"Improve {plan['name']} today",
        "description": f"{plan['project']} Resume line to add later: {plan['resume_line']}",
        "estimated_reward": 0,
        "priority": 11,
    })
    replace_today_tasks(user_id, tasks[:5])
    with get_cursor() as cur:
        cur.execute(
            "INSERT INTO alerts (user_id, message, created_at) VALUES (?, ?, ?)",
            (user_id, f"Skill task added: {plan['name']}", datetime.now().isoformat(timespec="seconds")),
        )
