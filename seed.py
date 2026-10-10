import json
from pathlib import Path
from sqlalchemy import select
from pydantic import BaseModel, Field
from app.models import Project, WallPostGate

class ProjectSource(BaseModel):
    slug: str = Field(pattern=r'^[a-z0-9]+(?:-[a-z0-9]+)*$', max_length=100)
    title: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1)
    longDescription: str
    tags: list[str]
    highlights: list[str]
    image: str
    github: str = ''
    demo: str = ''
    video: str = Field(default='', max_length=100)
    featured: bool = False

def seed(sessions, source_path=None):
    """Atomically add/update listed projects by slug; never delete other rows."""
    source = Path(source_path) if source_path else Path(__file__).parent / 'app/content/projects.json'
    data = json.loads(source.read_text(encoding='utf-8-sig'))
    if not isinstance(data, list):
        raise ValueError('projects.json must contain an array of project objects.')
    projects = [ProjectSource.model_validate(item) for item in data]
    slugs = [p.slug for p in projects]
    if len(slugs) != len(set(slugs)):
        raise ValueError('projects.json contains duplicate slugs. Each slug must be unique.')
    added = updated = 0
    with sessions() as db:
        if db.get(WallPostGate, 1) is None:
            db.add(WallPostGate(id=1, version=0))
        existing = {row.slug: row for row in db.scalars(select(Project))}
        for index, p in enumerate(projects):
            values = dict(title=p.title, category=p.category, summary=p.description, description=p.longDescription,
                          tech=p.tags, highlights=p.highlights, thumbnail_url=p.image, github_url=p.github, demo_url=p.demo,
                          video_id=p.video, is_featured=p.featured, sort_order=index)
            row = existing.get(p.slug)
            if row is None:
                db.add(Project(slug=p.slug, **values))
                added += 1
            elif any(getattr(row, key) != value for key, value in values.items()):
                for key, value in values.items():
                    setattr(row, key, value)
                updated += 1
        db.commit()
    return {'added': added, 'updated': updated}
    # Unlisted projects and wall/contact/like/report records are preserved.

if __name__ == '__main__':
    from app.core.config import Settings
    from app.db.session import database
    _, sessions = database(Settings().database_url)
    print(seed(sessions))
