from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.models import ContactMessage
from app.db.session import get_db
from app.schemas import ContactRequest, ContactResponse

router = APIRouter()


@router.post("", response_model=ContactResponse)
def contact(payload: ContactRequest, db: Session = Depends(get_db)) -> ContactResponse:
    message = ContactMessage(
        name=payload.name.strip(),
        email=str(payload.email).lower(),
        message=payload.message.strip(),
        status="new",
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return ContactResponse(
        id=message.id,
        status=message.status,
        message=f"Thanks {message.name}. The TrustMedAI-Chain team will respond soon.",
        created_at=message.created_at,
    )
