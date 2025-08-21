"""
Web/API-Specific Entrypoint for Non-Telephony Connections

This entrypoint is for web interfaces, API calls, and direct connections.
Uses the MainZenoAgent which is always active (no come in/leave commands).
"""

import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
import json
from datetime import datetime

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


class ConversationTranscript:
    """Handles collection and formatting of conversation transcripts."""

    def __init__(self):
        self.messages = []
        self.session_start_time = datetime.utcnow()

    def add_user_message(self, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Add a user message to the transcript."""
        self.messages.append({
            "role": "user",
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        })

    def add_agent_message(self, content: str, agent_type: str = "main_zeno", metadata: Optional[Dict[str, Any]] = None):
        """Add an agent message to the transcript."""
        self.messages.append({
            "role": "assistant",
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "agent_type": agent_type,
            "metadata": metadata or {}
        })

    def add_system_message(self, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Add a system message to the transcript."""
        self.messages.append({
            "role": "system",
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        })

    def get_transcript(self) -> List[Dict[str, Any]]:
        """Get the complete conversation transcript."""
        return self.messages.copy()

    def get_transcript_as_json(self) -> str:
        """Get the transcript as a JSON string."""
        return json.dumps(self.messages, indent=2)

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the conversation."""
        user_messages = [m for m in self.messages if m["role"] == "user"]
        agent_messages = [m for m in self.messages if m["role"] == "assistant"]

        return {
            "total_messages": len(self.messages),
            "user_messages": len(user_messages),
            "agent_messages": len(agent_messages),
            "session_duration_seconds": (datetime.utcnow() - self.session_start_time).total_seconds(),
            "start_time": self.session_start_time.isoformat(),
            "end_time": datetime.utcnow().isoformat()
        }


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
    print(f"🔍 DEBUGGING USER CONTEXT:")
    print(f"  Job metadata: {ctx.job.metadata}")
    print(f"  Remote participants count: {len(ctx.room.remote_participants)}")
    
    try:
        # Try first remote participant's metadata
        participants = list(ctx.room.remote_participants.values())
        if participants:
            participant = participants[0]
            print(f"  First participant: {participant.identity}")
            print(f"  First participant metadata: {participant.metadata}")
            md = participant.metadata
            if md:
                import json as _json
                user_ctx = _json.loads(md)
                print(f"✅ User context from participant metadata: {user_ctx}")
        
        # Fallback to job metadata
        if not user_ctx and ctx.job.metadata:
            import json as _json
            user_ctx = _json.loads(ctx.job.metadata)
            print(f"✅ User context from job metadata: {user_ctx}")
            
        if not user_ctx:
            print(f"❌ NO USER CONTEXT FOUND - using defaults")
        
    except Exception as e:
        print(f"❌ Error parsing user context: {e}")
        user_ctx = {}

    user_id = user_ctx.get("user_id")
    session_id_from_token = user_ctx.get("session_id")
    timezone = user_ctx.get("user_timezone")
    preferences = user_ctx.get("user_preferences") or {}
    user_name = user_ctx.get("user_name", "User")
    user_email = user_ctx.get("user_email")
    
    print(f"User context loaded: {user_name} ({user_email}) in {timezone} timezone")
    print(f"User preferences: {preferences}")

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
        user_name=user_name,
        user_email=user_email,
        timezone=timezone,
        preferences=preferences,
    )
    
    # Store agent reference for later access
    userdata_state._agent_ref = agent

    # Initialize conversation transcript collector
    userdata_state.conversation_transcript = ConversationTranscript()
    userdata_state.chat_buffer = []  # Keep for backward compatibility
    
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
        print(f"🎯 PARTICIPANT CONNECTED EVENT FIRED!")
        print(f"Participant {participant.identity} connected")
        
        # Extract user ID from participant identity (format: "user-{clerk_user_id}")
        clerk_user_id = None
        if participant.identity and participant.identity.startswith("user-"):
            clerk_user_id = participant.identity[5:]  # Remove "user-" prefix
            print(f"🔍 Extracted Clerk User ID: {clerk_user_id}")
        
        # Look up user in database to get their actual details
        user_data = {}
        if clerk_user_id:
            try:
                with session_scope() as db:
                    db_user = db.query(User).filter(User.clerk_user_id == clerk_user_id).first()
                    if db_user:
                        # Cast SQLAlchemy columns to avoid type checker issues
                        first_name = getattr(db_user, 'first_name', None) or ''
                        last_name = getattr(db_user, 'last_name', None) or ''
                        email = getattr(db_user, 'email', None)
                        timezone = getattr(db_user, 'timezone', None) or "UTC"
                        preferences = getattr(db_user, 'preferences', None) or {}
                        
                        user_data = {
                            "user_id": clerk_user_id,
                            "user_name": f"{first_name} {last_name}".strip() or "User",
                            "user_email": email,
                            "timezone": timezone,
                            "preferences": preferences
                        }
                        print(f"✅ Found user in database: {user_data}")
                    else:
                        print(f"❌ User {clerk_user_id} not found in database")
            except Exception as e:
                print(f"❌ Error looking up user in database: {e}")
        
        # Also try to extract from participant metadata (as backup)
        user_ctx_from_metadata: Dict[str, Any] = {}
        print(f"🔍 CHECKING PARTICIPANT METADATA:")
        print(f"  Participant metadata: {participant.metadata}")
        
        try:
            if participant.metadata:
                import json as _json
                user_ctx_from_metadata = _json.loads(participant.metadata)
                print(f"✅ User context from metadata: {user_ctx_from_metadata}")
        except Exception as e:
            print(f"❌ Error parsing participant metadata: {e}")
        
        # Combine database data with metadata (database takes priority)
        final_user_context = {**user_ctx_from_metadata, **user_data}
        
        # Update session userdata with the real user context
        if final_user_context and hasattr(session, 'userdata') and session.userdata:
            session.userdata.user_id = final_user_context.get("user_id")
            session.userdata.session_id = final_user_context.get("session_id")
            session.userdata.user_name = final_user_context.get("user_name", "User")
            session.userdata.user_email = final_user_context.get("user_email")
            session.userdata.timezone = final_user_context.get("timezone")
            session.userdata.preferences = final_user_context.get("preferences", {})
            
            print(f"✅ Updated session userdata with combined user context:")
            print(f"   User: {session.userdata.user_name} ({session.userdata.user_email})")
            print(f"   User ID: {session.userdata.user_id}")
            print(f"   Timezone: {session.userdata.timezone}")
            print(f"   Preferences: {session.userdata.preferences}")
            
            # CRITICAL: Update agent tools with user-specific credentials (async to avoid blocking STT)
            user_id = final_user_context.get("user_id")
            if (user_id and hasattr(session, 'userdata') and 
                hasattr(session.userdata, '_agent_ref') and 
                session.userdata._agent_ref is not None):
                agent = session.userdata._agent_ref
                if hasattr(agent, 'async_update_tools_with_user_context'):
                    # Run tool initialization in background to avoid blocking STT connection
                    import asyncio
                    asyncio.create_task(agent.async_update_tools_with_user_context(user_id))
                elif hasattr(agent, 'update_tools_with_user_context'):
                    # Fallback to sync version if async not available
                    print("⚠️ Using synchronous tool update - this may cause STT connection issues")
                    agent.update_tools_with_user_context(user_id)
        
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
                conversation_transcript = getattr(session.userdata, "conversation_transcript", None)
                if uid and sid:
                    from datetime import datetime
                    from core.storage import ChatHistory
                    with session_scope() as db:
                        # Save complete conversation transcript if available
                        if conversation_transcript:
                            full_transcript = conversation_transcript.get_transcript()
                            transcript_summary = conversation_transcript.get_summary()

                            # Save the complete conversation as one record
                            db.add(ChatHistory(
                                user_id=uid,
                                session_id=sid,
                                message_type="transcript",  # New type for complete transcripts
                                content=f"Conversation transcript with {transcript_summary['total_messages']} messages",
                                agent_type="main_zeno",
                                message_metadata=transcript_summary,
                                context_tags=["conversation_transcript", "complete_session"],
                                full_transcript=full_transcript,  # Store the complete transcript
                            ))

                        # Also save individual messages for backward compatibility
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

                        print(f"✅ Saved conversation transcript with {len(full_transcript) if conversation_transcript else 0} messages")
        except Exception as _e:
            print(f"Error finalizing session: {_e}")

    # Start the session
    await session.start(
        room=ctx.room,
        agent=agent,
        room_input_options=room_options,
    )
    
    # Check for any participants that might have connected while we were starting
    print(f"🔍 POST-START PARTICIPANT CHECK:")
    print(f"  Remote participants count: {len(ctx.room.remote_participants)}")
    for participant in ctx.room.remote_participants.values():
        print(f"  Found participant: {participant.identity}")
        # Manually trigger our user context extraction for existing participants
        on_participant_connected(participant)

    # Generate web-specific greeting (always active)
    if user_name and user_name != "User":
        greeting_instructions = f"Greet {user_name} warmly as Zeno, their personal daily planning assistant. Mention their name and offer your assistance. You're ready to help immediately."
    else:
        greeting_instructions = "Greet the user as Zeno, your daily planning assistant, and offer your assistance. You're ready to help immediately."
    
    await session.generate_reply(instructions=greeting_instructions)


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(
        entrypoint_fnc=web_entrypoint,
        # Set a different agent name for web connections
        agent_name="zeno-web-agent"
    ))
