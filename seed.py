import json
from pathlib import Path
from sqlalchemy import select, func
from app.models import Project, WallPostGate

def seed(sessions):
    with sessions() as db:
        if db.get(WallPostGate, 1) is None:
            db.add(WallPostGate(id=1, version=0))
            db.commit()
        if db.scalar(select(func.count()).select_from(Project)):
            return
        projects = json.loads(Path(__file__).parent.joinpath('app/content/projects.json').read_text(encoding='utf-8'))
        for index, p in enumerate(projects):
            db.add(Project(slug=p['slug'], title=p['title'], category=p['category'], summary=p['description'], description=p['longDescription'],
                           tech=p['tags'], highlights=p['highlights'], thumbnail_url=p['image'], github_url=p['github'], demo_url=p['demo'],
                           video_id=p['video'], is_featured=p['featured'], sort_order=index))
        db.commit()
    # Freedom Wall intentionally starts empty: no demo comments.

if __name__ == '__main__':
    from app.core.config import Settings
    from app.db.session import database
    _, sessions = database(Settings().database_url)
    seed(sessions)
