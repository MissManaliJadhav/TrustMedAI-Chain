"""
Chatbot API endpoints for TrustMedAI-Chain

Endpoints:
- POST /chat/sessions - Create new chat session
- GET /chat/sessions - List user's chat sessions
- GET /chat/sessions/{session_id} - Get session details
- POST /chat/messages - Send message and get response
- GET /chat/sessions/{session_id}/messages - Get chat history
- GET /chat/sessions/{session_id}/assessment - Get assessment summary
- POST /chat/sessions/{session_id}/export - Export session as diagnosis record
"""

from hashlib import sha256
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models import ChatMessage, ChatSession, DiagnosisArtifact, DiagnosisRecord, User
from app.schemas import (
    ChatAssessmentResponse,
    ChatMessageRequest,
    ChatMessageResponse,
    ChatSessionCreateRequest,
    ChatSessionResponse,
    ExportRequest,
)
from app.services.chatbot import (
    create_chat_session,
    generate_response,
    get_chat_history,
    get_session_assessment,
    save_chat_message,
)
from app.services.blockchain import (
    anchor_diagnosis,
    build_diagnosis_anchor_payload,
    hash_payload,
)
from app.services.reports import build_pdf_report
from app.services.storage import store_object

router = APIRouter(prefix="/chat", tags=["chatbot"])


@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    request: ChatSessionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatSessionResponse:
    """Create a new chat session."""
    try:
        session = create_chat_session(db, user_id=current_user.id, title=request.title)
        return ChatSessionResponse(
            id=session.id,
            title=session.title,
            status=session.status,
            conversation_stage=session.conversation_stage,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create chat session: {str(e)}",
        )


@router.get("/sessions", response_model=list[ChatSessionResponse])
def list_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ChatSessionResponse]:
    """List all chat sessions for the current user."""
    try:
        sessions = db.query(ChatSession).filter(ChatSession.user_id == current_user.id).order_by(ChatSession.updated_at.desc()).all()

        return [
            ChatSessionResponse(
                id=s.id,
                title=s.title,
                status=s.status,
                conversation_stage=s.conversation_stage,
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            for s in sessions
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list sessions: {str(e)}",
        )


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatSessionResponse:
    """Get a specific chat session."""
    try:
        session = db.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
        ).first()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found",
            )

        return ChatSessionResponse(
            id=session.id,
            title=session.title,
            status=session.status,
            conversation_stage=session.conversation_stage,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session: {str(e)}",
        )


@router.post("/messages")
def send_message(
    request: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Send a message and get chatbot response."""
    try:
        # Validate session_id is provided
        if not request.session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="session_id is required",
            )

        # Verify session ownership
        session = db.query(ChatSession).filter(ChatSession.id == request.session_id).first()
        if not session or session.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found",
            )

        # Save user message
        user_msg = save_chat_message(
            db,
            request.session_id,
            "user",
            request.content,
            request.message_type,
        )

        # Generate response
        response_text, metadata = generate_response(db, request.session_id, request.content)

        # Save assistant message
        assistant_msg = save_chat_message(
            db,
            request.session_id,
            "assistant",
            response_text,
            "text",
            metadata,
        )

        return {
            "user_message": ChatMessageResponse.model_validate(user_msg),
            "assistant_message": ChatMessageResponse.model_validate(assistant_msg),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send message: {str(e)}",
        )


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageResponse])
def get_session_messages(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ChatMessageResponse]:
    """Get chat history for a session."""
    try:
        # Verify session ownership
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session or session.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found",
            )

        messages = get_chat_history(db, session_id)
        return [ChatMessageResponse.model_validate(m) for m in messages]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get messages: {str(e)}",
        )


@router.get("/sessions/{session_id}/assessment", response_model=ChatAssessmentResponse)
def get_assessment(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatAssessmentResponse:
    """Get assessment summary for a session."""
    try:
        # Verify session ownership
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session or session.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found",
            )

        assessment = get_session_assessment(db, session_id)
        if not assessment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment not available",
            )

        return assessment
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get assessment: {str(e)}",
        )


@router.post("/sessions/{session_id}/export")
def export_session_as_diagnosis(
    session_id: str,
    request: ExportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Export chat session as a diagnosis record."""
    try:
        # Verify session ownership
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session or session.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found",
            )

        # Get assessment
        assessment = get_session_assessment(db, session_id)
        if not assessment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No assessment available to export",
            )

        # Create diagnosis record
        diagnosis = DiagnosisRecord(
            patient_id=current_user.id,
            disease_key=request.disease_key,
            prediction="Under Review - Chat Assessment",
            confidence=0.0,  # Will be updated by doctor
            metrics={
                "chat_assessment": True,
                "patient_profile": assessment.patient_summary.model_dump(),
                "symptoms": assessment.symptoms_summary.model_dump(),
                "risk_assessment": assessment.risk_assessment.model_dump(),
            },
            explanation={
                "chatbot_analysis": True,
                "conditions_suggested": [c.condition for c in assessment.possible_conditions],
            },
            trust_score=0.8,  # Initial trust score for AI-generated assessment
            aecs=0.0,
            blockchain_hash="pending",
            doctor_notes=f"Chatbot Assessment - Session {session_id}",
        )

        db.add(diagnosis)
        db.flush()
        diagnosis.blockchain_hash = hash_payload(
            build_diagnosis_anchor_payload(diagnosis)
        )
        db.commit()
        db.refresh(diagnosis)

        anchor_result = anchor_diagnosis(diagnosis)
        diagnosis.blockchain_status = anchor_result
        db.commit()
        db.refresh(diagnosis)

        report_content = build_pdf_report(diagnosis)
        report_filename = f"trustmedai-{diagnosis.id}.pdf"
        object_name = f"diagnoses/{diagnosis.id}/generated_report-{uuid4().hex}.pdf"
        stored = store_object(object_name, report_content, "application/pdf")
        report_artifact = DiagnosisArtifact(
            diagnosis_id=diagnosis.id,
            kind="generated_report",
            object_path=stored.object_path,
            original_filename=report_filename,
            content_type="application/pdf",
            size_bytes=len(report_content),
            sha256=sha256(report_content).hexdigest(),
        )
        diagnosis.report_object_path = stored.object_path
        db.add(report_artifact)
        db.commit()

        return {
            "diagnosis_id": diagnosis.id,
            "status": "created",
            "message": "Chat assessment has been converted to diagnosis record. A healthcare professional will review it.",
            "next_steps": [
                "A doctor will review your assessment",
                "You will receive feedback within 24-48 hours",
                "Additional tests may be recommended",
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export session: {str(e)}",
        )


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Delete a chat session."""
    try:
        # Verify session ownership
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session or session.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found",
            )

        # Delete related messages
        db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()

        # Delete session
        db.delete(session)
        db.commit()

        return {"status": "success", "message": "Chat session deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete session: {str(e)}",
        )
