"""Agent interaction routes for Zeno API."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class CallRequest(BaseModel):
    """Call scheduling request model."""
    phone_number: str
    scheduled_time: Optional[str] = None  # ISO format or "now"
    purpose: str = "general"  # "briefing", "update", "general"


class CallResponse(BaseModel):
    """Call response model."""
    call_id: str
    status: str
    scheduled_time: Optional[str]
    room_url: Optional[str]


@router.post("/call", response_model=CallResponse)
async def schedule_call(call_request: CallRequest):
    """Schedule a call with Zeno agent."""
    # TODO: Implement call scheduling with LiveKit
    raise HTTPException(status_code=501, detail="Call scheduling not implemented yet")


@router.get("/call/{call_id}")
async def get_call_status(call_id: str):
    """Get status of a scheduled call."""
    # TODO: Implement call status retrieval
    raise HTTPException(status_code=501, detail="Call status not implemented yet")


@router.post("/call/{call_id}/cancel")
async def cancel_call(call_id: str):
    """Cancel a scheduled call."""
    # TODO: Implement call cancellation
    return {"message": f"Call {call_id} cancelled successfully"}


@router.get("/sessions")
async def get_active_sessions():
    """Get active agent sessions."""
    # TODO: Implement session retrieval
    raise HTTPException(status_code=501, detail="Session retrieval not implemented yet")
