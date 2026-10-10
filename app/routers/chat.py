from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import limiter
from app.models import ChatLog
from app.schemas import Chat
from app.services.chat_service import reply

router = APIRouter(prefix='/api/chat')
@router.post('')
@limiter.limit('20/minute')
def chat(request: Request, payload: Chat, db: Session = Depends(get_db)):
    result = reply(payload.message, db)
    if request.app.state.settings.enable_chat_logs:
        db.add_all([ChatLog(session_id=payload.session_id, role='user', content=payload.message), ChatLog(session_id=payload.session_id, role='assistant', content=result)])
        db.commit()
    return {'reply': result}
