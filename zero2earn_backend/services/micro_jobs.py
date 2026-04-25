from __future__ import annotations

MICRO_JOB_PORTALS = [
    {
        'id': 'clickworker',
        'name': 'Clickworker',
        'category': 'Microtasks',
        'beginner': True,
        'payout_speed': 'Medium',
        'earning_range': '₹200-₹1,500/day',
        'country_fit': 'Worldwide',
        'url': 'https://www.clickworker.com/clickworker-job/',
        'why': 'Quick-start platform for surveys, writing, categorization, and web research.',
    },
    {
        'id': 'toloka',
        'name': 'Toloka',
        'category': 'AI data tasks',
        'beginner': True,
        'payout_speed': 'Fast',
        'earning_range': '₹150-₹1,000/day',
        'country_fit': 'Worldwide',
        'url': 'https://toloka.ai/tolokers/',
        'why': 'Useful for annotation, search relevance, and small AI evaluation tasks.',
    },
    {
        'id': 'oneforma',
        'name': 'OneForma',
        'category': 'AI projects',
        'beginner': False,
        'payout_speed': 'Medium',
        'earning_range': '₹300-₹3,000/day',
        'country_fit': 'Worldwide',
        'url': 'https://jobs.oneforma.com/',
        'why': 'Better for language, annotation, and long-running AI data projects.',
    },
    {
        'id': 'microworkers',
        'name': 'Microworkers',
        'category': 'Simple tasks',
        'beginner': True,
        'payout_speed': 'Medium',
        'earning_range': '₹100-₹800/day',
        'country_fit': 'Worldwide',
        'url': 'https://www.microworkers.com/',
        'why': 'Many small web, signup, testing, and categorization tasks.',
    },
    {
        'id': 'appen',
        'name': 'Appen CrowdGen',
        'category': 'Crowd work / AI',
        'beginner': False,
        'payout_speed': 'Slow-Medium',
        'earning_range': '₹300-₹2,500/day',
        'country_fit': 'Varies by project',
        'url': 'https://crowdgen.com/',
        'why': 'Longer-term annotation and AI evaluation opportunities.',
    },
    {
        'id': 'timebucks',
        'name': 'TimeBucks',
        'category': 'Quick cash',
        'beginner': True,
        'payout_speed': 'Fast',
        'earning_range': '₹50-₹500/day',
        'country_fit': 'Worldwide',
        'url': 'https://timebucks.com/',
        'why': 'Entry-level earning path while building profile elsewhere.',
    },
]


def list_micro_jobs() -> list[dict]:
    return MICRO_JOB_PORTALS
