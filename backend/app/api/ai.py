
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.database import get_db

from backend.app.ai.copilot import (
    generate_compliance_explanation,
    answer_compliance_question
)

router = APIRouter(
    prefix="/api/ai",
    tags=["AI Compliance Copilot"]
)


class CopilotQuestion(BaseModel):
    customer_id: str
    question: str


@router.get("/explain/{customer_id}")
def explain_customer(
    customer_id: str,
    db: Session = Depends(get_db)
):
    return generate_compliance_explanation(
        db,
        customer_id
    )


@router.post("/chat")
def chat_with_copilot(
    request: CopilotQuestion,
    db: Session = Depends(get_db)
):
    return answer_compliance_question(
        db,
        request.customer_id,
        request.question
    )
