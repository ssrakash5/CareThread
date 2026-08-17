from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ThreadEvent
from app.schemas import ThreadEventOut

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/threads/{thread_id}", response_model=list[ThreadEventOut])
def audit_thread(thread_id: str, db: Session = Depends(get_db)):
    stmt = select(ThreadEvent).where(ThreadEvent.thread_id == thread_id).order_by(ThreadEvent.created_at.asc())
    return db.execute(stmt).scalars().all()
