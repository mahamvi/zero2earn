from __future__ import annotations

import json
import re
from io import BytesIO
from typing import Any

from docx import Document
from pypdf import PdfReader

COMMON_SKILLS = [
    'Medical Writing', 'Clinical Research', 'Diabetes Care', 'Healthcare Consulting', 'Telemedicine',
    'AI Content', 'Machine Learning', 'Python', 'Excel', 'SQL', 'Data Entry', 'Customer Support',
    'Content Writing', 'Copywriting', 'Research', 'Project Management', 'LinkedIn', 'Resume Writing',
    'Editing', 'Proofreading', 'Digital Marketing', 'Sales', 'Virtual Assistance'
]


def extract_text_from_upload(filename: str, content: bytes) -> str:
    lower = filename.lower()
    if lower.endswith('.pdf'):
        reader = PdfReader(BytesIO(content))
        return '\n'.join(page.extract_text() or '' for page in reader.pages)
    if lower.endswith('.docx'):
        doc = Document(BytesIO(content))
        return '\n'.join(p.text for p in doc.paragraphs)
    return content.decode('utf-8', errors='ignore')


def normalize_text(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


def detect_skills(text: str) -> list[str]:
    compact = text.lower()
    found = [skill for skill in COMMON_SKILLS if skill.lower() in compact]
    return found[:12]


def infer_track(text: str, skills: list[str]) -> str:
    combined = f"{text} {' '.join(skills)}".lower()
    if any(k in combined for k in ['medical', 'clinical', 'healthcare', 'doctor', 'diabetes']):
        if any(k in combined for k in ['ai', 'writing', 'content', 'research']):
            return 'Medical writing + AI + consulting'
        return 'Healthcare remote roles'
    if any(k in combined for k in ['data entry', 'excel', 'virtual assistance']):
        return 'Micro earning + operations'
    if any(k in combined for k in ['python', 'sql', 'machine learning']):
        return 'Tech + AI remote roles'
    return 'General remote'


def missing_keywords(track: str, skills: list[str]) -> list[str]:
    target = {
        'Medical writing + AI + consulting': ['Portfolio', 'LinkedIn', 'Writing Samples', 'Research'],
        'Healthcare remote roles': ['Telemedicine', 'Documentation', 'Excel'],
        'Micro earning + operations': ['Excel', 'Data Entry', 'Customer Support'],
        'Tech + AI remote roles': ['Python', 'SQL', 'Machine Learning', 'Portfolio'],
        'General remote': ['LinkedIn', 'Excel', 'Resume Writing'],
    }.get(track, ['LinkedIn', 'Excel'])
    current = {s.lower() for s in skills}
    return [k for k in target if k.lower() not in current][:5]


def optimize_headline(skills: list[str], track: str, name: str) -> str:
    lead = ', '.join(skills[:3]) if skills else 'Remote-ready professional'
    return f'{name} | {track} | {lead}'


def optimize_summary(text: str, skills: list[str], track: str) -> str:
    base = normalize_text(text)[:700]
    skill_line = ', '.join(skills[:6]) if skills else 'communication, adaptability, and structured execution'
    return (
        f'Profile focus: {track}. Key strengths: {skill_line}. '
        f'This profile is best positioned for outcome-driven remote opportunities and first-income acceleration. '
        f'Optimized summary seed: {base[:350]}'
    )


def analyze_resume(text: str, name: str = 'Candidate') -> dict[str, Any]:
    clean = normalize_text(text)
    skills = detect_skills(clean)
    track = infer_track(clean, skills)
    gaps = missing_keywords(track, skills)
    return {
        'skills': skills,
        'track': track,
        'missing_keywords': gaps,
        'headline': optimize_headline(skills, track, name),
        'summary': optimize_summary(clean, skills, track),
        'resume_text': clean,
    }


def skills_json(skills: list[str]) -> str:
    return json.dumps(skills)



def resume_status(user: dict) -> dict[str, Any]:
    """Return resume-first onboarding status for the SaaS flow."""
    resume_text = str(user.get('resume_text') or '').strip()
    skills = user.get('skills') or []
    if isinstance(skills, str):
        try:
            skills = json.loads(skills)
        except Exception:
            skills = []
    has_resume = len(resume_text) >= 80
    return {
        'has_resume': has_resume,
        'resume_length': len(resume_text),
        'headline': user.get('headline') or '',
        'summary': user.get('summary') or '',
        'skills': skills,
        'track': user.get('track') or 'General remote',
        'next_step': 'Upload or paste resume to unlock accurate matching.' if not has_resume else 'Resume analyzed. Review optimizer and open Jobs.',
    }


def optimize_resume_layer(text: str, name: str = 'Candidate') -> dict[str, Any]:
    """Analyze + produce a practical resume improvement layer."""
    analysis = analyze_resume(text, name)
    skills = analysis['skills']
    gaps = analysis['missing_keywords']
    track = analysis['track']
    headline = analysis['headline']
    summary = analysis['summary']
    bullets = []
    if skills:
        bullets.append(f"Built experience around {', '.join(skills[:4])} with structured execution and measurable contribution.")
    bullets.append('Improved workflow quality through consistent documentation, communication, and task completion.')
    bullets.append('Adapted quickly to remote work requirements, tools, deadlines, and outcome-focused delivery.')
    ats_keywords = list(dict.fromkeys(skills + gaps))[:12]
    score = min(92, 35 + len(skills) * 5 + (15 if len(text) > 600 else 0) + (10 if '@' in text or 'linkedin' in text.lower() else 0))
    return {
        **analysis,
        'resume_score': score,
        'optimized_headline': headline,
        'optimized_summary': summary,
        'recommended_bullets': bullets,
        'ats_keywords': ats_keywords,
        'job_search_focus': _job_search_focus(track, skills),
    }


def _job_search_focus(track: str, skills: list[str]) -> list[str]:
    combined = f"{track} {' '.join(skills)}".lower()
    if any(x in combined for x in ['python', 'sql', 'machine learning', 'tech']):
        return ['remote analyst', 'junior developer', 'qa tester', 'data analyst', 'ai operations']
    if any(x in combined for x in ['writing', 'content', 'research', 'medical']):
        return ['content writer', 'research assistant', 'medical writer', 'documentation specialist']
    if any(x in combined for x in ['support', 'customer']):
        return ['customer support', 'chat support', 'email support', 'virtual assistant']
    if any(x in combined for x in ['excel', 'data entry', 'operations']):
        return ['data entry', 'operations assistant', 'back office', 'virtual assistant']
    return ['remote assistant', 'entry remote jobs', 'microtasks', 'freelance support']
