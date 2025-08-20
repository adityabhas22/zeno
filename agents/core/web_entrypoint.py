"""
Web/API-Specific Entrypoint for Non-Telephony Connections

This entrypoint is for web interfaces, API calls, and direct connections.
Uses the MainZenoAgent which is always active (no come in/leave commands).
"""

import sys
from pathlib import Path
from typing import Optional, Dict, Any

# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables first
from dotenv import load_dotenv
load_dotenv()

from livekit import agents
from livekit.agents import AgentSession, RoomInputOptions
from livekit.plugins import deepgram, openai, silero, noise_cancellation

from config.settings import get_settings
from agents.core.main_zeno_agent import MainZenoAgent, MainZenoState
from core.storage import session_scope, UserSession, User


async def web_entrypoint(ctx: agents.JobContext):
    """
    Web/API-specific entrypoint for non-telephony connections.
    
    This entrypoint:
    - Always uses MainZenoAgent (always active, no activation required)
    - Optimizes for web/API connections
    - Provides immediate responsiveness
    """
    settings = get_settings()
    
    print(f"Zeno web agent starting for room: {ctx.room.name}")
    print(f"Connection type: web/API")
    print(f"Current participants: {len(ctx.room.remote_participants)}")
    
    # Extract user context from participant metadata (set by token)
    # Fallback to ctx.job.metadata if needed
    user_ctx: Dict[str, Any] = {}
    try:
        # Try first remote participant's metadata
        participants = ctx.room.remote_participants
        if participants:
            md = participants[0].metadata
            if md:
                import json as _json
                user_ctx = _json.loads(md)
        # Fallback to job metadata
        if not user_ctx and ctx.job.metadata:
            import json as _json
            user_ctx = _json.loads(ctx.job.metadata)
    except Exception:
        user_ctx = {}

    user_id = user_ctx.get("user_id")
    session_id_from_token = user_ctx.get("session_id")
    timezone = user_ctx.get("user_timezone")
    preferences = user_ctx.get("user_preferences") or {}

    # Validate user exists if provided
    if user_id:
        try:
            with session_scope() as db:
                db.query(User).filter(User.clerk_user_id == user_id).first()
        except Exception:
            pass

    # Use MainZenoAgent for web/API connections
    agent = MainZenoAgent()
    userdata_state = MainZenoState(
        user_id=user_id,
        session_id=session_id_from_token,
        timezone=timezone,
        preferences=preferences,
    )
    
    # Web-optimized room options
    room_options = RoomInputOptions(
        noise_cancellation=noise_cancellation.BVCTelephony(),  # Use same for consistency
    )
    
    # Don't target specific participant initially
    target_identity: Optional[str] = None
    if target_identity is not None:
        room_options.participant_identity = target_identity

    # Create session with main agent
    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="en"),
        llm=openai.LLM(model="gpt-5"),
        tts=deepgram.TTS(model="aura-2-thalia-en"),
        vad=silero.VAD.load(),
        turn_detection="vad",
        max_tool_steps=settings.agent_max_tool_steps,
        preemptive_generation=settings.agent_preemptive_generation,
        allow_interruptions=settings.agent_allow_interruptions,
        userdata=userdata_state,
    )

    # Handle participant events
    @ctx.room.on("participant_connected")
    def on_participant_connected(participant):
        print(f"Participant {participant.identity} connected")
        # Nothing special for always-active agent

    @ctx.room.on("participant_disconnected")
    def on_participant_disconnected(participant):
        print(f"Participant {participant.identity} disconnected")
        # Batch write chat history and end session if we have identifiers
        try:
            if getattr(session, "userdata", None) and session.userdata:
                uid = getattr(session.userdata, "user_id", None)
                sid = getattr(session.userdata, "session_id", None)
                chat_buffer = getattr(session.userdata, "chat_buffer", [])
                if uid and sid:
                    from datetime import datetime
                    from core.storage import ChatHistory
                    with session_scope() as db:
                        # Append buffered messages
                        for m in chat_buffer:
                            db.add(ChatHistory(
                                user_id=uid,
                                session_id=sid,
                                message_type=m.get("message_type", "system"),
                                content=m.get("content", ""),
                                agent_type="main_zeno",
                                message_metadata={},
                                context_tags=[],
                            ))
                        # Mark session as ended
                        db.query(UserSession).filter(UserSession.id == sid).update({
                            "is_active": False,
                            "ended_at": datetime.utcnow(),
                        })
        except Exception as _e:
            print(f"Error finalizing session: {_e}")

    # Start the session
    await session.start(
        room=ctx.room,
        agent=agent,
        room_input_options=room_options,
    )

    # Generate web-specific greeting (always active)
    greeting_instructions = "Greet the user as Zeno, your daily planning assistant, and offer your assistance. You're ready to help immediately."
    await session.generate_reply(instructions=greeting_instructions)


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(
        entrypoint_fnc=web_entrypoint,
        # Set a different agent name for web connections
        agent_name="zeno-web-agent"
    ))
