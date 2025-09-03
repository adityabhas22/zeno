"""
Telephony-Specific Entrypoint for Phone Calls

This entrypoint is specifically for telephony calls and sets the correct agent name
for LiveKit dispatch rules. Uses the PhoneTelephonyAgent with come in/leave features.
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
from livekit.agents import AgentSession, RoomInputOptions
from livekit.plugins import deepgram, openai, silero, noise_cancellation

from config.settings import get_settings
from agents.core.phone_telephony_agent import PhoneTelephonyAgent, PhoneTelephonyState
from tools.postcall import handle_call_end


async def telephony_entrypoint(ctx: agents.JobContext):
    """
    Telephony-specific entrypoint for phone calls.
    
    This entrypoint:
    - Always uses PhoneTelephonyAgent (with come in/leave features)
    - Sets the correct agent name for dispatch rules
    - Optimizes for telephony connections
    """
    settings = get_settings()
    
    # Extract metadata for telephony context
    metadata = {}
    phone_number = None
    call_purpose = "general"
    
    try:
        if ctx.job.metadata:
            metadata = json.loads(ctx.job.metadata)
            phone_number = metadata.get("phone_number")
            call_purpose = metadata.get("purpose", "general")
    except (json.JSONDecodeError, KeyError):
        pass
    
    print(f"Zeno telephony agent starting for room: {ctx.room.name}")
    print(f"Phone number: {phone_number or 'inbound call'}")
    print(f"Call purpose: {call_purpose}")
    print(f"Current participants: {len(ctx.room.remote_participants)}")
    
    # Use PhoneTelephonyAgent for all telephony calls
    agent = PhoneTelephonyAgent()
    userdata_state = PhoneTelephonyState()
    
    # Telephony-optimized room options
    room_options = RoomInputOptions(
        noise_cancellation=noise_cancellation.BVCTelephony(),
    )
    
    # Don't target specific participant initially
    target_identity: Optional[str] = None
    if target_identity is not None:
        room_options.participant_identity = target_identity

    # Create session with telephony agent
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
        # Reset assistant state for new participants (starts inactive)
        if hasattr(session, 'userdata') and session.userdata:
            session.userdata.zeno_active = False

    @ctx.room.on("participant_disconnected")
    def on_participant_disconnected(participant):
        print(f"Participant {participant.identity} disconnected")
        # Reset assistant state when participants disconnect
        if hasattr(session, 'userdata') and session.userdata:
            session.userdata.zeno_active = False
        
        # Handle cleanup
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

    # Generate telephony-specific greeting
    if phone_number is None:
        # Inbound telephony call
        greeting_instructions = "Greet the user as Zeno, your daily planning assistant. Let them know you're ready to help and they can say 'Hey Zeno' or 'Come in' to activate you."
    else:
        # Outbound telephony call - purpose-specific greeting
        if call_purpose == "briefing":
            greeting_instructions = "Greet the user warmly and let them know you're calling to provide their daily briefing. Ask if now is a good time."
        elif call_purpose == "reminder":
            greeting_instructions = "Greet the user and mention you're calling with a scheduled reminder or update."
        else:
            greeting_instructions = "Greet the user and let them know you're calling to check in on their day."
    
    await session.generate_reply(instructions=greeting_instructions)


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(
        entrypoint_fnc=telephony_entrypoint,
        # Set the agent name expected by dispatch rules
        agent_name="my-telephony-agent"
    ))
