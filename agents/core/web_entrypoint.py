"""
Web/API-Specific Entrypoint for Non-Telephony Connections

This entrypoint is for web interfaces, API calls, and direct connections.
Uses the MainZenoAgent which is always active (no come in/leave commands).
"""

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
from livekit.agents import AgentSession, RoomInputOptions
from livekit.plugins import deepgram, openai, silero, noise_cancellation

from config.settings import get_settings
from agents.core.main_zeno_agent import MainZenoAgent, MainZenoState


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
    
    # Use MainZenoAgent for web/API connections
    agent = MainZenoAgent()
    userdata_state = MainZenoState()
    
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
        # MainZenoAgent is always active - no state changes needed

    @ctx.room.on("participant_disconnected")
    def on_participant_disconnected(participant):
        print(f"Participant {participant.identity} disconnected")
        # MainZenoAgent doesn't have activation state

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
