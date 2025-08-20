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
from tools.postcall import handle_call_end


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
        print(f"Participant {participant.identity} connected")
        # Reset assistant state for new participants
        if hasattr(session, 'userdata') and session.userdata:
            if connection_type == "telephony":
                session.userdata.zeno_active = False  # Phone agent starts inactive
            # Main agent doesn't have activation state - always ready

    @ctx.room.on("participant_disconnected")
    def on_participant_disconnected(participant):
        print(f"Participant {participant.identity} disconnected")
        # Reset assistant state when participants disconnect
        if hasattr(session, 'userdata') and session.userdata:
            if connection_type == "telephony":
                session.userdata.zeno_active = False
        
        # Handle cleanup with enhanced Zeno features
        try:
            handle_call_end(session, participant)
        except Exception as e:
            print(f"Error in handle_call_end: {e}")

    # Start the session
    await session.start(
        room=ctx.room,
        agent=agent,
        room_input_options=room_options,
    )

    # Generate appropriate greeting based on connection type
    greeting_instructions = router.get_greeting_for_connection(connection_type, metadata)
    await session.generate_reply(instructions=greeting_instructions)


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(
        entrypoint_fnc=smart_entrypoint,
        # No specific agent name - will be set per agent type in separate entrypoints
    ))
