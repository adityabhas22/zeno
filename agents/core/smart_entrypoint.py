"""
Smart Entrypoint for Zeno Agents

Enhanced entrypoint that automatically routes to the appropriate agent based on connection type.
Replaces the individual agent entrypoints with intelligent routing.
"""

import json
import sys
from pathlib import Path
from typing import Optional

# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables first
from dotenv import load_dotenv
load_dotenv()

from livekit import agents
from livekit.agents import AgentSession
from livekit.plugins import deepgram, openai, silero

from config.settings import get_settings
from agents.core.agent_router import get_agent_router
from core.storage import session_scope, User
from agents.core.web_entrypoint import ConversationTranscript
import asyncio


async def smart_entrypoint(ctx: agents.JobContext):
    """
    Smart entrypoint that routes to appropriate agent based on connection type.
    
    - Telephony calls → PhoneTelephonyAgent (with come in/leave features)
    - Web/API calls → MainZenoAgent (always active)
    """
    settings = get_settings()
    router = get_agent_router()
    
    # Detect connection type and get metadata
    connection_type, metadata = router.detect_connection_type(ctx)
    
    print(f"Zeno smart entrypoint starting for room: {ctx.room.name}")
    print(f"Detected connection type: {connection_type}")
    print(f"Metadata: {metadata}")
    print(f"Current participants: {len(ctx.room.remote_participants)}")
    
    # Get appropriate agent, state, and room options
    agent, userdata_state, room_options = router.get_agent_for_connection(connection_type, metadata)
    
    print(f"Selected agent: {type(agent).__name__}")
    
    # Don't target specific participant initially - let the agent handle any participant
    target_identity: Optional[str] = None
    
    # Only set participant_identity if we have a target
    if target_identity is not None:
        room_options.participant_identity = target_identity

    # Attach agent reference to userdata for later tool initialization
    try:
        setattr(userdata_state, "_agent_ref", agent)
    except Exception:
        pass

    # Create session with appropriate agent and state
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

    # Handle participant events for dynamic targeting
    @ctx.room.on("participant_connected")
    def on_participant_connected(participant):
        print("🎯 PARTICIPANT CONNECTED EVENT FIRED!")
        print(f"Participant {participant.identity} connected")

        # Extract user ID from participant identity (format: "user-{clerk_user_id}")
        clerk_user_id = None
        if participant.identity and participant.identity.startswith("user-"):
            clerk_user_id = participant.identity[5:]
            print(f"🔍 Extracted Clerk User ID: {clerk_user_id}")

        # Look up user details in DB (best-effort)
        user_data = {}
        if clerk_user_id:
            try:
                with session_scope() as db:
                    db_user = db.query(User).filter(User.clerk_user_id == clerk_user_id).first()
                    if db_user:
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
                            "preferences": preferences,
                        }
                        print(f"✅ Found user in database: {user_data}")
                    else:
                        print(f"❌ User {clerk_user_id} not found in database")
            except Exception as e:
                print(f"❌ Error looking up user in database: {e}")

        # Also parse participant metadata
        user_ctx_from_metadata = {}
        print("🔍 CHECKING PARTICIPANT METADATA:")
        print(f"  Participant metadata: {participant.metadata}")
        try:
            if participant.metadata:
                user_ctx_from_metadata = json.loads(participant.metadata)
                print(f"✅ User context from metadata: {user_ctx_from_metadata}")
        except Exception as e:
            print(f"❌ Error parsing participant metadata: {e}")

        # Merge contexts (DB takes priority)
        final_user_context = {**user_ctx_from_metadata, **user_data}

        # Always initialize transcript + buffer when userdata exists
        if getattr(session, 'userdata', None):
            try:
                session.userdata.conversation_transcript = ConversationTranscript()
            except Exception:
                session.userdata.conversation_transcript = None
            try:
                session.userdata.chat_buffer = []
            except Exception:
                pass

        # Update session userdata if we have context
        if final_user_context and getattr(session, 'userdata', None):
            session.userdata.user_id = final_user_context.get("user_id")
            session.userdata.session_id = final_user_context.get("session_id")
            session.userdata.user_name = final_user_context.get("user_name", "User")
            session.userdata.user_email = final_user_context.get("user_email")
            session.userdata.timezone = final_user_context.get("timezone")
            session.userdata.preferences = final_user_context.get("preferences", {})

            print("✅ Updated session userdata with combined user context:")
            print(f"   User: {session.userdata.user_name} ({session.userdata.user_email})")
            print(f"   User ID: {session.userdata.user_id}")
            print(f"   Timezone: {session.userdata.timezone}")
            print(f"   Preferences: {session.userdata.preferences}")

            # For telephony, ensure starts inactive
            if connection_type == "telephony":
                setattr(session.userdata, 'zeno_active', False)

            # Initialize per-user Google tools asynchronously
            user_id = final_user_context.get("user_id")
            agent_ref = getattr(session.userdata, "_agent_ref", None)
            if user_id and agent_ref is not None:
                if hasattr(agent_ref, 'async_update_tools_with_user_context'):
                    asyncio.create_task(agent_ref.async_update_tools_with_user_context(user_id))
                elif hasattr(agent_ref, 'update_tools_with_user_context'):
                    print("⚠️ Using synchronous tool update - may block briefly")
                    agent_ref.update_tools_with_user_context(user_id)

    @ctx.room.on("participant_disconnected")
    def on_participant_disconnected(participant):
        print(f"Participant {participant.identity} disconnected")
        if hasattr(session, 'userdata') and session.userdata and connection_type == "telephony":
            session.userdata.zeno_active = False

    # Start the session
    await session.start(
        room=ctx.room,
        agent=agent,
        room_input_options=room_options,
    )

    # Post-start participant check (handle already-connected participants)
    print("🔍 POST-START PARTICIPANT CHECK:")
    print(f"  Remote participants count: {len(ctx.room.remote_participants)}")
    for p in ctx.room.remote_participants.values():
        print(f"  Found participant: {p.identity}")
        on_participant_connected(p)

    # Generate appropriate greeting based on connection type
    greeting_instructions = router.get_greeting_for_connection(connection_type, metadata)
    await session.generate_reply(instructions=greeting_instructions)


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(
        entrypoint_fnc=smart_entrypoint,
        # No specific agent name - will be set per agent type in separate entrypoints
    ))
