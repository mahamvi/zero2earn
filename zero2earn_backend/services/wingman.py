from __future__ import annotations

from typing import Any


def _safe(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    text = str(value).strip()
    return [text] if text else []


def _win_probability(score: int, matched_count: int, missing_count: int) -> int:
    score = max(0, min(100, int(score)))
    base = 18 + int(score * 0.72)
    base += min(matched_count * 3, 10)
    base -= min(missing_count * 4, 12)
    return max(12, min(92, base))


def _job_family(job: dict) -> str:
    text = f"{_safe(job.get('title'))} {_safe(job.get('description'))}".lower()
    if any(x in text for x in ["writer", "content", "copy", "research", "documentation"]):
        return "writing"
    if any(x in text for x in ["qa", "test", "automation", "engineer", "developer", "api", "python", "sql"]):
        return "technical"
    if any(x in text for x in ["support", "customer", "success", "chat", "email support"]):
        return "support"
    if any(x in text for x in ["operations", "assistant", "coordinator", "executive", "analyst"]):
        return "operations"
    return "general"


def _build_proposal(job: dict, user: dict) -> str:
    title = _safe(job.get("title"), "this role")
    company = _safe(job.get("company"), "your team")
    matched = _as_list(job.get("matched_skills"))
    missing = _as_list(job.get("missing_skills"))
    headline = _safe(user.get("headline"))
    summary = _safe(user.get("summary"))
    user_skills = _as_list(user.get("skills"))

    strongest = matched[:4] if matched else user_skills[:4]
    strongest_text = ", ".join(strongest) if strongest else "relevant practical skills"
    family = _job_family(job)

    opener = f"Hi {company} team,\n\nI’m interested in your {title} role because it aligns well with my profile and the kind of work I can contribute to effectively."
    identity = f"My background: {headline}." if headline else "I bring a flexible, execution-focused profile suited to remote and outcome-driven work."

    if family == "technical":
        body = f"I already have useful alignment in {strongest_text}, and I can contribute through structured execution, problem solving, testing discipline, and fast adaptation to existing workflows."
    elif family == "writing":
        body = f"My profile aligns well in {strongest_text}, and I can contribute with clear written communication, research-backed work, organized output, and consistent delivery quality."
    elif family == "support":
        body = f"I have relevant alignment in {strongest_text}, and I can contribute through responsiveness, clarity, process-following, and dependable day-to-day execution."
    elif family == "operations":
        body = f"My fit is strongest in {strongest_text}, and I can contribute by bringing structure, follow-through, documentation, coordination, and reliable execution."
    else:
        body = f"My profile shows direct alignment in {strongest_text}, and I can contribute through practical execution, communication, and learning speed."

    gap_line = ""
    if missing:
        gap_line = f"I also understand there may be gaps around {', '.join(missing[:2])}, and I am comfortable ramping up quickly where needed."

    summary_line = f"Additional context: {summary[:220].strip()}" if summary else ""
    closer = "If selected, I can begin by understanding your priorities quickly, aligning with the workflow, and contributing useful output from the first phase itself.\n\nBest regards"

    parts = [opener, identity, body]
    if gap_line:
        parts.append(gap_line)
    if summary_line:
        parts.append(summary_line)
    parts.append(closer)
    return "\n\n".join(parts)


def wingman_payload(job: dict, user: dict) -> dict:
    title = _safe(job.get("title"), "Untitled role")
    company = _safe(job.get("company"), "Unknown company")
    portal_url = _safe(job.get("apply_url")) or "#"

    reasons = _as_list(job.get("reasons"))
    matched = _as_list(job.get("matched_skills"))
    missing = _as_list(job.get("missing_skills"))

    if not reasons:
        if matched:
            reasons.append(f"Matched skills: {', '.join(matched[:5])}")
        if "remote" in _safe(job.get("location")).lower() or "remote" in _safe(job.get("description")).lower():
            reasons.append("Remote-friendly role")
        if not reasons:
            reasons.append("General fit based on title and resume alignment")

    match_score = int(job.get("match_score", 50))
    win_probability = _win_probability(match_score, len(matched), len(missing))

    checklist = [
        "Open the source portal and review the full description once.",
        "Keep the first 2 lines of the proposal specific to the job title.",
        "Use 2–4 strongest matched skills from your resume.",
    ]
    if missing:
        checklist.append(f"Address the gap briefly: {', '.join(missing[:2])}.")
    checklist.append("Submit the application and mark it applied in Zero2Earn.")

    return {
        "job_id": _safe(job.get("id")),
        "title": title,
        "company": company,
        "portal_url": portal_url,
        "match_score": match_score,
        "win_probability": win_probability,
        "reasons": reasons,
        "missing": missing,
        "checklist": checklist,
        "proposal": _build_proposal(job, user),
    }
