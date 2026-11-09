"""
Conversation endpoints (all under /api). Both need the session token.

    POST /conversation/turn      the applicant says or types something; the
                                 agent understands it, saves what is valid,
                                 reads back critical values and replies
    GET  /conversation/messages  the transcript, for resuming a session
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_application
from app.core.database import get_db
from app.models import Application, ConversationMessage, MessageRole
from app.schemas.agent import (
    AgentTurnRequest,
    AgentTurnResponse,
    ConversationHistory,
    ConversationMessageRead,
)
from app.services.agent_service import AgentService

router = APIRouter(prefix="/conversation", tags=["conversation"])


@router.post("/turn", response_model=AgentTurnResponse)
def take_turn(
    payload: AgentTurnRequest,
    application: Application = Depends(get_current_application),
    db: Session = Depends(get_db),
):
    return AgentService(db).turn(application, payload.text, payload.source)


@router.get("/messages", response_model=ConversationHistory)
def read_messages(
    limit: int = Query(100, ge=1, le=500),
    application: Application = Depends(get_current_application),
    db: Session = Depends(get_db),
):
    statement = (
        select(ConversationMessage)
        .where(
            ConversationMessage.application_id == application.id,
            ConversationMessage.role != MessageRole.TOOL,  # tool records are not shown
        )
        .order_by(ConversationMessage.id.desc())
        .limit(limit)
    )
    rows = list(reversed(list(db.execute(statement).scalars())))
    return ConversationHistory(
        messages=[
            ConversationMessageRead(
                id=m.id, role=m.role.value, channel=m.channel.value, content=m.content,
                field_id=m.field_id, created_at=m.created_at,
            )
            for m in rows
        ]
    )