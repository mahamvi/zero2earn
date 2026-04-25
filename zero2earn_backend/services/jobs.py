import random

def score_job(user, job):
    score = 0

    keywords = (user.get("headline", "") + " " + user.get("summary", "")).lower()

    job_text = (job["title"] + " " + job["description"]).lower()

    matches = 0
    for word in keywords.split():
        if word in job_text:
            matches += 1

    score = min(100, matches * 5)

    # Boost for domain match
    if "medical" in keywords and "medical" in job_text:
        score += 20

    if "ai" in keywords and "ai" in job_text:
        score += 15

    return min(score, 100)


def get_jobs(user):
    jobs = [
        {
            "id": 1,
            "title": "AI Medical Writer",
            "company": "HealthTech AI",
            "location": "Remote",
            "description": "Write medical + AI content",
            "apply_url": "https://example.com"
        },
        {
            "id": 2,
            "title": "Clinical Research Analyst",
            "company": "Global Trials",
            "location": "Remote",
            "description": "Analyze clinical data",
            "apply_url": "https://example.com"
        },
        {
            "id": 3,
            "title": "AI Data Labeling Specialist",
            "company": "AI Labs",
            "location": "Remote",
            "description": "Label AI datasets",
            "apply_url": "https://example.com"
        },
        {
            "id": 4,
            "title": "Healthcare Content Writer",
            "company": "MediContent",
            "location": "Remote",
            "description": "Create health blogs",
            "apply_url": "https://example.com"
        },
        {
            "id": 5,
            "title": "Telemedicine Consultant",
            "company": "eClinic",
            "location": "Remote",
            "description": "Consult patients online",
            "apply_url": "https://example.com"
        }
    ]

    scored_jobs = []

    for job in jobs:
        score = score_job(user, job)

        if score < 30:
            continue  # FILTER LOW QUALITY

        job["match_score"] = score
        job["win_probability"] = min(100, score - random.randint(5, 15))

        scored_jobs.append(job)

    # Sort high score first
    scored_jobs.sort(key=lambda x: x["match_score"], reverse=True)

    return {"jobs": scored_jobs}