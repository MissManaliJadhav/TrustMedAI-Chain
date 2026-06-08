from fastapi import APIRouter

from app.schemas import ContactRequest

router = APIRouter()


@router.post("")
def contact(payload: ContactRequest) -> dict[str, str]:
    return {"status": "received", "message": f"Thanks {payload.name}. The TrustMedAI-Chain team will respond soon."}
