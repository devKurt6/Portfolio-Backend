from pathlib import Path
from sqlalchemy import select
from app.models import Project

def reply(message, session):
    text = message.lower()
    projects = session.scalars(select(Project).where(Project.is_published).order_by(Project.sort_order)).all()
    for p in projects:
        if p.slug.replace('-', ' ') in text or p.title.lower() in text:
            return p.title + ': ' + p.description
    if any(word in text for word in ['project', 'work', 'built']):
        return 'Kurt’s projects include: ' + '; '.join(p.title for p in projects) + '. Browse the Projects page for details.'
    if any(word in text for word in ['contact', 'email', 'hire']):
        return 'You can contact Kurt at kurtdecena41@gmail.com or use the Contact page.'
    if any(word in text for word in ['skill', 'about', 'experience', 'who']):
        return Path(__file__).parents[1].joinpath('content/bio.txt').read_text(encoding='utf-8').strip()
    return 'I can help with Kurt’s projects, skills, experience, and contact details. What would you like to know?'

def notify_contact(_message):
    """Future email-provider hook. Deliberately sends no email."""
