"""
Agent Session API Routes

Handles authenticated agent session creation and management.
"""

import json
import uuid
from typing import Dict, Any, Optional, cast
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.middleware.clerk_auth import (
    get_current_user_id,
    get_current_user,
)
from core.storage import get_database_session, User, UserSession, session_scope
from config.settings import get_settings

router = APIRouter()
settings = get_settings()


class AgentSessionRequest(BaseModel):
    """Request model for creating agent sessions."""
    agent_type: str = "main_zeno"  # "main_zeno", "daily_planning"
    session_type: str = "web"  # "web", "phone", "api"
    initial_context: Optional[Dict[str, Any]] = None


class AgentSessionResponse(BaseModel):
    """Response model for agent session creation."""
    session_id: str
    room_name: str
    livekit_token: str
    livekit_url: str
    agent_type: str
    user_id: str


@router.post("/create", response_model=AgentSessionResponse)
async def create_agent_session(
    request: AgentSessionRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """
    Create a new agent session for the authenticated user.
    
    This endpoint:
    1. Validates the authenticated user
    2. Creates a UserSession record in the database
    3. Generates a LiveKit room and token with user metadata
    4. Returns connection details for the frontend
    """
    # Extract user info from Clerk JWT (required)
    clerk_user_id = str(user.get("clerk_user_id")) if user.get("clerk_user_id") else str(uuid.uuid4())
    user_email = user.get("email") or f"{clerk_user_id}@example.local"
    first_name = user.get("first_name")
    last_name = user.get("last_name")
    
    # Validate user exists in our database
    db_user = db.query(User).filter(User.clerk_user_id == clerk_user_id).first()
    if not db_user:
        # Auto-upsert user
        db_user = User(
            clerk_user_id=clerk_user_id,
            email=user_email,
            first_name=first_name,
            last_name=last_name,
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
    
    # Create UserSession record
    session_id = str(uuid.uuid4())
    room_name = f"zeno-session-{session_id}"
    
    user_session = UserSession(
        id=session_id,
        user_id=clerk_user_id,
        session_type=request.session_type,
        agent_type=request.agent_type,
        conversation_state={},
        agent_context=request.initial_context or {},
        shared_data={
            "user_preferences": db_user.preferences,
            "timezone": db_user.timezone
        },
        is_active=True
    )
    
    db.add(user_session)
    db.commit()
    db.refresh(user_session)
    
    # Generate LiveKit token with user metadata
    try:
        from livekit.api import AccessToken, VideoGrants
        
        # Create access token with user context in metadata
        token = AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
        token.with_identity(f"user-{clerk_user_id}")

        # Avoid truthiness on SQLAlchemy Column by casting instance attributes
        first_name_val = cast(Optional[str], getattr(db_user, "first_name", None))
        last_name_val = cast(Optional[str], getattr(db_user, "last_name", None))
        display_name = f"{first_name_val or 'User'} {last_name_val or ''}".strip()
        token.with_name(display_name)
        token.with_grants(VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=True,
            can_subscribe=True
        ))
        
        # CRITICAL: Add user context to metadata for agent access
        # Cast to optional strings to avoid SQLAlchemy Column type issues
        first_name = cast(Optional[str], getattr(db_user, "first_name", None))
        last_name = cast(Optional[str], getattr(db_user, "last_name", None))
        username_from_jwt = None
        if isinstance(user, dict):
            username_from_jwt = (user.get("full_payload", {}) or {}).get("username")
        user_name = f"{first_name or ''} {last_name or ''}".strip() or username_from_jwt or "User"
        
        # Enhanced user preferences with defaults
        user_prefs = cast(Optional[dict], getattr(db_user, "preferences", None)) or {}
        enhanced_preferences = {
            **user_prefs,
            "display_name": user_name,
            "greeting_style": user_prefs.get("greeting_style", "friendly"),
            "briefing_detail": user_prefs.get("briefing_detail", "detailed"),
            "communication_style": user_prefs.get("communication_style", "conversational"),
            "time_format": user_prefs.get("time_format", "12hour"),
        }
        
        token.with_metadata(json.dumps({
            "user_id": clerk_user_id,
            "session_id": session_id,
            "agent_type": request.agent_type,
            "user_email": db_user.email,
            "user_name": user_name,
            "user_first_name": first_name,
            "user_last_name": last_name,
            "user_timezone": db_user.timezone,
            "user_preferences": enhanced_preferences
        }))
        
        livekit_token = token.to_jwt()
        
    except Exception as e:
        # Rollback session creation if token generation fails
        db.delete(user_session)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create LiveKit token: {str(e)}"
        )
    
    return AgentSessionResponse(
        session_id=session_id,
        room_name=room_name,
        livekit_token=livekit_token,
        livekit_url=settings.livekit_url,
        agent_type=request.agent_type,
        user_id=clerk_user_id
    )


@router.get("/status/{session_id}")
async def get_session_status(
    session_id: str,
    clerk_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_database_session)
):
    """Get the status of a specific agent session."""
    
    # Find session and verify ownership
    user_session = db.query(UserSession).filter(
        UserSession.id == session_id,
        UserSession.user_id == clerk_user_id
    ).first()
    
    if not user_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or access denied"
        )
    
    return {
        "session_id": user_session.id,
        "agent_type": user_session.agent_type,
        "session_type": user_session.session_type,
        "is_active": user_session.is_active,
        "started_at": user_session.started_at,
        "last_activity_at": user_session.last_activity_at,
        "ended_at": user_session.ended_at
    }


@router.post("/end/{session_id}")
async def end_agent_session(
    session_id: str,
    clerk_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_database_session)
):
    """End an active agent session."""

    
    # Find session and verify ownership
    user_session = db.query(UserSession).filter(
        UserSession.id == session_id,
        UserSession.user_id == clerk_user_id
    ).first()
    
    if not user_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or access denied"
        )
    
    # Mark session as ended
    from datetime import datetime
    
    # Update session fields using SQLAlchemy update
    db.query(UserSession).filter(
        UserSession.id == session_id
    ).update({
        "is_active": False,
        "ended_at": datetime.utcnow()
    })
    
    db.commit()
    
    return {
        "message": "Session ended successfully",
        "session_id": session_id,
        "ended_at": user_session.ended_at
    }


@router.get("/my-sessions")
async def get_my_sessions(
    clerk_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_database_session),
    limit: int = 10
):
    """Get current user's recent agent sessions."""

    
    sessions = db.query(UserSession).filter(
        UserSession.user_id == clerk_user_id
    ).order_by(UserSession.started_at.desc()).limit(limit).all()
    
    return [
        {
            "session_id": session.id,
            "agent_type": session.agent_type,
            "session_type": session.session_type,
            "is_active": session.is_active,
            "started_at": session.started_at,
            "ended_at": session.ended_at
        }
        for session in sessions
    ]
