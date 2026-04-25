from __future__ import annotations

from typing import Any
from urllib.parse import quote_plus

import httpx


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(str(x) for x in value)
    return str(value)


def _extract_skills(user: dict) -> list[str]:
    skills = user.get("skills", []) or []
    out = []
    for s in skills:
        s = str(s).strip().lower()
        if s and s not in out:
            out.append(s)
    return out


def _build_portal_links(title: str) -> dict[str, str]:
    q = quote_plus(title)
    return {
        "linkedin": f"https://www.linkedin.com/jobs/search/?keywords={q}",
        "indeed_india": f"https://in.indeed.com/jobs?q={q}",
        "naukri": f"https://www.naukri.com/{q}-jobs",
        "foundit": f"https://www.foundit.in/search/{q}",
        "internshala": f"https://internshala.com/jobs/{q}",
    }


def _detect_level(text: str) -> str:
    t = text.lower()
    if any(x in t for x in ["senior", "lead", "principal", "staff", "architect", "head"]):
        return "senior"
    if any(x in t for x in ["mid", "specialist", "engineer ii", "developer ii"]):
        return "mid"
    if any(x in t for x in ["intern", "junior", "entry", "associate", "assistant", "trainee", "fresher"]):
        return "entry"
    return "general"


def _detect_category(text: str) -> str:
    t = text.lower()
    if any(x in t for x in ["writer", "content", "copywriter", "editor", "documentation", "research"]):
        return "writing"
    if any(x in t for x in ["qa", "automation", "developer", "engineer", "api", "python", "sql", "frontend", "backend", "testing"]):
        return "tech"
    if any(x in t for x in ["support", "customer", "success", "chat", "email support"]):
        return "support"
    if any(x in t for x in ["analyst", "operations", "coordinator", "assistant", "executive", "etl", "bi"]):
        return "operations"
    if any(x in t for x in ["design", "ui", "ux", "graphic", "figma"]):
        return "design"
    if any(x in t for x in ["sales", "marketing", "seo", "growth"]):
        return "marketing"
    return "general"


def _score_job(job: dict, user: dict) -> dict[str, Any]:
    skills = _extract_skills(user)
    title = _safe_text(job.get("title"))
    desc = _safe_text(job.get("description"))
    company = _safe_text(job.get("company"))
    location = _safe_text(job.get("location"))
    salary = _safe_text(job.get("salary_hint"))
    text = f"{title} {desc} {company} {location}".lower()
    title_lower = title.lower()

    matched = [s for s in skills if s and s in text]

    score = 8
    score += min(len(matched) * 14, 56)

    for s in skills:
        if s and s in title_lower:
            score += 8

    if "remote" in text:
        score += 8

    if salary and salary.lower() != "not listed":
        score += 4

    if any(x in text for x in ["content", "writer", "research", "documentation"]):
        score += 4
    if any(x in text for x in ["qa", "testing", "automation", "analyst", "assistant", "support"]):
        score += 4

    level = _detect_level(text)
    if level == "entry":
        score += 6
    elif level == "mid":
        score += 2
    elif level == "senior":
        score -= 10

    missing = []
    critical_keywords = ["python", "sql", "excel", "automation", "api", "testing", "communication", "portfolio", "analytics", "documentation"]
    for keyword in critical_keywords:
        if keyword in text and keyword not in matched and keyword not in skills:
            missing.append(keyword)

    score -= min(len(missing) * 4, 20)
    score = max(18, min(96, score))

    reasons = []
    if matched:
        reasons.append(f"Matched skills: {', '.join(matched[:5])}")
    if "remote" in text:
        reasons.append("Remote-friendly role")
    if level == "entry":
        reasons.append("Entry-accessible opportunity")
    elif level == "mid":
        reasons.append("Mid-level opportunity")
    elif level == "senior":
        reasons.append("More advanced opportunity")
    if salary and salary.lower() != "not listed":
        reasons.append("Salary information available")
    if not reasons:
        reasons.append("General fit based on role title and resume alignment")

    win_probability = max(10, min(93, int(score * 0.82) + 6 - min(len(missing) * 2, 8)))

    return {
        "match_score": score,
        "win_probability": win_probability,
        "matched_skills": matched,
        "missing_skills": missing[:5],
        "reasons": reasons,
        "level": level,
        "category": _detect_category(text),
        "remote_only": "remote" in text,
    }


def _normalize_remotive(item: dict) -> dict:
    title = _safe_text(item.get("title")) or "Untitled role"
    company = _safe_text(item.get("company_name")) or "Unknown company"
    apply_url = _safe_text(item.get("url")) or _safe_text(item.get("job_url")) or "#"
    location = _safe_text(item.get("candidate_required_location")) or "Remote"
    description = _safe_text(item.get("description"))
    salary = _safe_text(item.get("salary")) or "Not listed"
    job_id = f"remotive-{_safe_text(item.get('id')) or abs(hash(title + company))}"
    return {
        "id": job_id,
        "title": title,
        "company": company,
        "source": "Remotive",
        "apply_url": apply_url,
        "location": location,
        "salary_hint": salary,
        "description": description,
        "portal_links": _build_portal_links(title),
    }


def _normalize_remoteok(item: dict) -> dict:
    title = _safe_text(item.get("position") or item.get("title")) or "Untitled role"
    company = _safe_text(item.get("company")) or "Unknown company"
    apply_url = _safe_text(item.get("url")) or "#"
    location = _safe_text(item.get("location")) or "Remote"
    tags = _safe_text(item.get("tags"))
    description = (_safe_text(item.get("description")) + " " + tags).strip()
    salary = _safe_text(item.get("salary_min")) or "Not listed"
    job_id = f"remoteok-{_safe_text(item.get('id')) or abs(hash(title + company))}"
    return {
        "id": job_id,
        "title": title,
        "company": company,
        "source": "RemoteOK",
        "apply_url": apply_url,
        "location": location,
        "salary_hint": salary,
        "description": description,
        "portal_links": _build_portal_links(title),
    }


def _normalize_arbeitnow(item: dict) -> dict:
    title = _safe_text(item.get("title")) or "Untitled role"
    company = _safe_text(item.get("company_name")) or "Unknown company"
    apply_url = _safe_text(item.get("url")) or "#"
    location = _safe_text(item.get("location")) or "Remote"
    tags = _safe_text(item.get("tags"))
    description = (_safe_text(item.get("description")) + " " + tags).strip()
    slug = _safe_text(item.get("slug"))
    job_id = f"arbeitnow-{slug or abs(hash(title + company))}"
    return {
        "id": job_id,
        "title": title,
        "company": company,
        "source": "Arbeitnow",
        "apply_url": apply_url,
        "location": location,
        "salary_hint": "Not listed",
        "description": description,
        "portal_links": _build_portal_links(title),
    }


async def fetch_live_jobs() -> list[dict]:
    jobs: list[dict] = []
    timeout = httpx.Timeout(15.0, connect=8.0)

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers={"User-Agent": "Zero2Earn/1.0"}) as client:
        try:
            r = await client.get("https://remotive.com/api/remote-jobs")
            r.raise_for_status()
            data = r.json()
            for item in data.get("jobs", [])[:60]:
                jobs.append(_normalize_remotive(item))
        except Exception:
            pass

        try:
            r = await client.get("https://remoteok.com/api")
            r.raise_for_status()
            data = r.json()
            if isinstance(data, list):
                for item in data[1:61]:
                    if isinstance(item, dict):
                        jobs.append(_normalize_remoteok(item))
        except Exception:
            pass

        try:
            r = await client.get("https://www.arbeitnow.com/api/job-board-api")
            r.raise_for_status()
            data = r.json()
            for item in data.get("data", [])[:60]:
                jobs.append(_normalize_arbeitnow(item))
        except Exception:
            pass

    seen = set()
    deduped = []
    for job in jobs:
        key = (job["title"].strip().lower(), job["company"].strip().lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(job)

    return deduped[:120]


def recommend_jobs(
    live_jobs: list[dict],
    user: dict,
    query: str = "",
    source: str = "",
    level: str = "",
    min_score: int = 0,
    category: str = "",
    remote_only: bool = False,
) -> list[dict]:
    scored = []
    q = query.strip().lower()
    source = source.strip().lower()
    level = level.strip().lower()
    category = category.strip().lower()

    for job in live_jobs:
        s = _score_job(job, user)
        merged = dict(job)
        merged["match_score"] = s["match_score"]
        merged["win_probability"] = s["win_probability"]
        merged["matched_skills"] = s["matched_skills"]
        merged["missing_skills"] = s["missing_skills"]
        merged["reasons"] = s["reasons"]
        merged["level"] = s["level"]
        merged["experience_level"] = s["level"]
        merged["category"] = s["category"]
        merged["remote_only"] = s["remote_only"]

        hay = f"{merged['title']} {merged['company']} {merged['description']} {merged['category']}".lower()
        if q and q not in hay:
            continue
        if source and merged["source"].lower() != source:
            continue
        if level and merged["level"] != level:
            continue
        if category and merged["category"] != category:
            continue
        if remote_only and not merged["remote_only"]:
            continue
        if merged["match_score"] < int(min_score or 0):
            continue
        scored.append(merged)

    scored.sort(key=lambda x: (x["match_score"], x["win_probability"]), reverse=True)
    return scored[:40]
