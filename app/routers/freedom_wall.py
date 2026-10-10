import math
from datetime import datetime, timezone, timedelta
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy import select, func, or_, and_, update
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import WallMessage, WallLike, WallReport, WallPostGate
from app.schemas import WallPost, Report
from app.core.security import visitor, ip_hash, limiter
from app.services.moderation import moderate
from app.services.wall_service import wall_json

router = APIRouter(prefix='/api/freedom-wall/messages')

def accessible(db, request, message_id):
    # Lock the parent row before toggling counters on PostgreSQL; SQLite uses an
    # early write lock, so concurrent toggles cannot read the same old state.
    db.execute(update(WallMessage).where(WallMessage.id == message_id).values(like_count=WallMessage.like_count))
    row = db.scalar(select(WallMessage).where(WallMessage.id == message_id).with_for_update())
    own = visitor(request)
    if row is None or not (row.status == 'approved' or row.status == 'pending' and row.visitor_hash == own):
        raise HTTPException(404, 'Message not found.')
    return row, own

@router.get('')
def messages(request: Request, sort: Literal['new', 'top'] = 'new', limit: int = Query(default=6, ge=1, le=50), offset: int = Query(default=0, ge=0), db: Session = Depends(get_db)):
    own = visitor(request, required=False)
    reported = select(WallReport.message_id).where(WallReport.reporter_hash == ip_hash(request))
    condition = and_(or_(WallMessage.status == 'approved', and_(WallMessage.status == 'pending', WallMessage.visitor_hash == own) if own else False), WallMessage.id.not_in(reported))
    total = db.scalar(select(func.count()).select_from(WallMessage).where(condition))
    ordering = [WallMessage.like_count.desc(), WallMessage.created_at.desc(), WallMessage.id.desc()] if sort == 'top' else [WallMessage.created_at.desc(), WallMessage.id.desc()]
    rows = db.scalars(select(WallMessage).where(condition).order_by(*ordering).offset(offset).limit(limit)).all()
    return dict(items=[wall_json(r, db, own) for r in rows], total=total, nextOffset=offset+len(rows))

@router.post('')
@limiter.limit('10/minute')
def post(request: Request, payload: WallPost, db: Session = Depends(get_db)):
    own = visitor(request)
    if payload.website:
        return dict(id='ignored', name=payload.name, text=payload.text, emoji=payload.emoji, likes=0, timestamp=int(datetime.now(timezone.utc).timestamp()*1000), liked=False, status='published', mine=True)
    status = moderate(payload.name, payload.text)
    hashed = ip_hash(request)
    settings = request.app.state.settings
    now = datetime.now(timezone.utc)
    # Serialize quota check with writes (across workers sharing the same DB).
    db.execute(update(WallPostGate).where(WallPostGate.id == 1).values(version=WallPostGate.version + 1))
    previous = db.scalar(select(WallMessage).where(WallMessage.ip_hash == hashed).order_by(WallMessage.created_at.desc()).limit(1))
    if previous:
        elapsed = (now - previous.created_at.replace(tzinfo=timezone.utc)).total_seconds()
        if elapsed < settings.wall_post_seconds:
            raise HTTPException(429, 'Please wait before posting again.', headers={'Retry-After': str(math.ceil(settings.wall_post_seconds-elapsed))})
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    count = db.scalar(select(func.count()).select_from(WallMessage).where(WallMessage.ip_hash == hashed, WallMessage.created_at >= midnight))
    if count >= settings.wall_daily_cap:
        raise HTTPException(429, 'You have reached today’s posting limit.', headers={'Retry-After': str(math.ceil((midnight+timedelta(days=1)-now).total_seconds()))})
    row = WallMessage(display_name=payload.name, content=payload.text, emoji=payload.emoji, status=status, ip_hash=hashed, visitor_hash=own)
    db.add(row)
    db.commit()
    return wall_json(row, db, own)

@router.post('/{message_id}/like')
@limiter.limit('60/minute')
def like(request: Request, message_id: int, db: Session = Depends(get_db)):
    row, own = accessible(db, request, message_id)
    found = db.scalar(select(WallLike).where(WallLike.message_id == row.id, WallLike.visitor_id == own))
    if found:
        db.delete(found)
    else:
        db.add(WallLike(message_id=row.id, visitor_id=own))
    db.flush()
    row.like_count = db.scalar(select(func.count()).select_from(WallLike).where(WallLike.message_id == row.id))
    db.commit()
    return wall_json(row, db, own)

@router.post('/{message_id}/report')
@limiter.limit('10/hour')
def report(request: Request, message_id: int, payload: Report, db: Session = Depends(get_db)):
    row, _ = accessible(db, request, message_id)
    hashed = ip_hash(request)
    if not db.scalar(select(WallReport.id).where(WallReport.message_id == row.id, WallReport.reporter_hash == hashed)):
        db.add(WallReport(message_id=row.id, reporter_hash=hashed, reason=payload.reason))
        db.flush()
        row.report_count = db.scalar(select(func.count()).select_from(WallReport).where(WallReport.message_id == row.id))
        if row.report_count >= request.app.state.settings.wall_report_threshold:
            row.status = 'hidden'
        db.commit()
    return {'ok': True}
