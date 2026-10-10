from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.core.security import limiter, ip_hash
from app.db.session import get_db
from app.models import ContactMessage
from app.schemas import Contact
from app.services.chat_service import notify_contact

router = APIRouter(prefix='/api/contact')
@router.post('')
@limiter.limit('3/hour')
def contact(request: Request, payload: Contact, db: Session = Depends(get_db)):
    if not payload.website:
        row = ContactMessage(name=payload.name, email=str(payload.email), message=payload.message, ip_hash=ip_hash(request))
        db.add(row)
        db.commit()
        notify_contact(row)
    return {'ok': True}
