from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.security import admin
from app.db.session import get_db
from app.models import WallMessage, ContactMessage
from app.services.wall_service import wall_json

router = APIRouter(prefix='/api/admin', dependencies=[Depends(admin)])
@router.get('/wall/pending')
def pending(db: Session = Depends(get_db)):
    return [wall_json(r, db, '') for r in db.scalars(select(WallMessage).where(WallMessage.status.in_(['pending', 'hidden'])).order_by(WallMessage.created_at.desc()).limit(100))]

@router.post('/wall/{message_id}/{action}')
def moderate(message_id: int, action: str, db: Session = Depends(get_db)):
    status = {'approve': 'approved', 'reject': 'rejected', 'hide': 'hidden'}.get(action)
    row = db.get(WallMessage, message_id)
    if not status or row is None:
        raise HTTPException(404, 'Message or action not found.')
    row.status = status
    db.commit()
    return {'ok': True}

@router.get('/contact')
def contacts(db: Session = Depends(get_db)):
    return [dict(id=r.id, name=r.name, email=r.email, message=r.message, created_at=r.created_at.isoformat(), handled=r.handled) for r in db.scalars(select(ContactMessage).order_by(ContactMessage.created_at.desc()).limit(100))]
