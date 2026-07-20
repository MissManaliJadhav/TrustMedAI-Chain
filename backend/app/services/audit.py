from __future__ import annotations

from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.db.models import AuditEvent, User
from app.services.blockchain import hash_payload


def request_context(request: Request | None) -> dict[str, Any]:
    if request is None:
        return {}
    return {
        "ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    }


def record_audit_event(
    db: Session,
    *,
    actor: User | None,
    action: str,
    resource_type: str,
    resource_id: str | None,
    metadata: dict[str, Any] | None = None,
    request: Request | None = None,
) -> AuditEvent:
    payload = {
        "actor_id": actor.id if actor else None,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "metadata": metadata or {},
        "request": request_context(request),
    }
    event = AuditEvent(
        actor_id=actor.id if actor else None,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        payload_hash=hash_payload(payload),
        metadata_json={**(metadata or {}), **request_context(request)},
    )
    db.add(event)
    return event
