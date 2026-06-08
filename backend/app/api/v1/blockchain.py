from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.db.models import User
from app.db.session import get_db
from app.services.blockchain import explorer_snapshot

router = APIRouter()


@router.get("/explorer")
def explorer(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("audit:view")),
) -> dict:
    return explorer_snapshot(db)


@router.get("/nodes")
def nodes(_: User = Depends(require_permission("blockchain:manage"))) -> dict:
    return {
        "fabric": [
            {"name": "fabric-peer-0", "status": "gateway-configured"},
            {"name": "fabric-orderer-0", "status": "network-profile-required"},
        ],
        "ethereum": [{"name": "trust-ledger-contract", "status": "configured-for-real-transactions"}],
    }
