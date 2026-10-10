from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import Project
from app.services.wall_service import project_json

router = APIRouter(prefix='/api/projects')

@router.get('')
def projects(category: str = Query(default='', max_length=100), q: str = Query(default='', max_length=200), db: Session = Depends(get_db)):
    rows = db.scalars(select(Project).where(Project.is_published).order_by(Project.sort_order)).all()
    return [project_json(p) for p in rows if (not category or category == p.category) and (not q or q.lower() in (' '.join([p.title, p.summary, *p.tech])).lower())]

@router.get('/{slug}')
def project(slug: str, db: Session = Depends(get_db)):
    row = db.scalar(select(Project).where(Project.slug == slug, Project.is_published))
    if row is None:
        raise HTTPException(404, 'Project not found.')
    return project_json(row)
