"""
Zeno Agent - Main AI Assistant

The primary agent for Zeno, providing daily planning assistance and voice interaction.
Renamed and enhanced from the original Jarvis implementation.
"""

import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Optional, Any, Dict, Tuple
from dataclasses import dataclass


# Add project root to Python path to allow imports from any location
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables first
from dotenv import load_dotenv
load_dotenv()

from livekit import agents
from livekit.agents import Agent, AgentSession, StopResponse, RoomInputOptions, function_tool, RunContext
from livekit.agents import ChatContext, ChatMessage
from livekit.plugins import openai, deepgram, cartesia, silero, noise_cancellation

from config.settings import get_settings
from agents.core.workspace_agent import get_workspace_tools
from agents.core.daily_planning_agent import DailyPlanningAgent
from agents.workflows.morning_briefing import MorningBriefingWorkflow
from tools.postcall import handle_call_end


@dataclass
class ZenoState:
    """State management for Zeno agent sessions."""
    zeno_active: bool = False
    user_id: Optional[str] = None
    session_start_time: Optional[str] = None
    daily_briefing_requested: bool = False
    current_context: str = "general"  # "briefing", "planning", "general"
    current_agent: str = "zeno"  # "zeno", "daily_planning"
    planning_session: Optional[Dict[str, Any]] = None  # Store interactive planning session data


class ZenoAgent(Agent):
    """
    Main Zeno AI Agent for daily planning and voice assistance.
    
    Enhanced from the original Jarvis agent with:
    - Daily planning capabilities
    - Morning briefing workflows
    - Task management integration
    - Calendar awareness
    """
    
    def __init__(self) -> None:
        settings = get_settings()
        
        # Initialize specialized agents and workflows
        self.daily_planning_agent = DailyPlanningAgent()
        self.briefing_workflow = MorningBriefingWorkflow()
        
        # Collect all tools before calling super().__init__
        all_tools = []
        
        # Add Google Workspace tools
        all_tools.extend(get_workspace_tools())
        
        # Note: Real-time IST context will be provided through agent instructions
        
        super().__init__(
            instructions="""You are Zeno, an AI-powered daily planning assistant.

**CRITICAL TIME ZONE INSTRUCTIONS:**
- Today's date is August 20, 2025 (Tuesday) in Indian Standard Time (IST, UTC+05:30)
- ALWAYS use IST timezone (+05:30) for all calendar events
- Format calendar event times as: YYYY-MM-DDTHH:mm:ss+05:30
- When users say "today" = 2025-08-20, "tomorrow" = 2025-08-21
- Default event duration is 1 hour unless specified otherwise

Your primary role is to help users plan and organize their day through:

1. **Morning Briefings & Interactive Planning**: Provide comprehensive daily support including:
   - Today's calendar events and schedule
   - Weather and traffic conditions
   - Priority tasks and reminders
   - Interactive daily planning sessions with goal-setting
   - Automatic Google Docs creation and email drafting

2. **Task Management**: Help users:
   - Add, modify, and prioritize daily tasks
   - Set reminders and deadlines
   - Break down complex projects into manageable steps
   - Review task completion and progress

3. **Calendar Integration**: Assist with:
   - Schedule review and conflict detection
   - Meeting preparation and summaries
   - Time blocking for important tasks
   - Travel time and location planning
   - **ALWAYS use IST timezone (+05:30) for all calendar events**

4. **Agent Delegation**: 
   - Switch to specialized daily planning mode for focused task management
   - Use daily planning agent for comprehensive briefings and task organization
   - Return to main mode for general assistance

5. **Proactive Communication**: 
   - Call users at scheduled times for briefings
   - Provide timely reminders and updates
   - Check in on task progress throughout the day
   - Offer planning suggestions and optimizations

**Interaction Style**:
- Be conversational but efficient
- Provide clear, actionable information
- Ask clarifying questions when needed
- Maintain context throughout conversations
- Adapt to user preferences and patterns

**Agent Switching**:
- When users request detailed daily planning, task management, or morning briefings, use the switch_to_daily_planning tool
- Switch with phrases like "let's plan my day", "help me organize tasks", "give me a day brief", "start interactive planning"
- The daily planning agent automatically provides: day brief → planning questions → document creation
- Day brief includes: calendar events, emails, weather, priority tasks, organized for voice delivery
- The daily planning agent can return to main mode when tasks are complete

**Activation**:
- Respond to "Hey Zeno" or "Zeno" for activation
- Support one-shot commands even when not actively listening
- Deactivate with "That's all" or "Goodbye Zeno"

Remember: You're here to make daily planning effortless and ensure users start each day prepared and organized.
""",
            tools=all_tools,
        )


    def _normalize(self, text: str) -> str:
        """Lowercase and collapse punctuation to spaces for robust matching."""
        t = text.lower()
        t = re.sub(r"[\s,;:._\-]+", " ", t).strip()
        return t

    def _is_activation(self, text: str) -> bool:
        """Check if text contains Zeno activation phrases."""
        t = self._normalize(text)
        return any(
            phrase in t
            for phrase in [
                "zeno in",
                "come in",
                "join",
                "step in",
                "hey zeno",
                "wake",        # Added simple wake command
                "wake up",     # Added wake up command
            ]
        )

    def _is_deactivation(self, text: str) -> bool:
        """Check if text contains Zeno deactivation phrases."""
        t = self._normalize(text)
        return any(
            phrase in t
            for phrase in [
                "zeno out",
                "leave",
                "dismiss", 
                "stand down",
                "that's all",
                "goodbye",
                "stop",
            ]
        )

    def _extract_one_shot(self, text: str) -> Optional[str]:
        """Extract one-shot command if present."""
        # Accept variations like "Hey, Zeno -- do X", "Zeno: do X", "Zeno do X"
        # Normalize punctuation and allow common misspellings
        t = self._normalize(text)
        # fast exit if zeno not present
        if not re.match(r"^(hey\s+)?zeno\b", t):
            return None
        # strip the vocative prefix
        tail = re.sub(r"^(hey\s+)?zeno\b\s*", "", t).strip()
        if not tail or self._is_activation(text) or self._is_deactivation(text):
            return None
        return tail

    def _maybe_strip_zeno_prefix(self, text: str) -> str:
        """Remove Zeno vocative prefix from text."""
        return re.sub(r"^(?:hey\s+)?zeno\b\s*", "", text, flags=re.IGNORECASE)

    @function_tool()
    async def switch_to_daily_planning(
        self,
        context: RunContext,
    ) -> Tuple[DailyPlanningAgent, str]:
        """Switch to the specialized daily planning agent for comprehensive planning, task management, and briefings.

        This agent can:
        - Conduct interactive daily planning sessions
        - Generate morning briefings with calendar and weather
        - Manage tasks and priorities
        - Create Google Docs with planning summaries
        - Draft emails with daily plans
        
        Returns:
            The DailyPlanningAgent instance (triggers agent handoff)
        """
        # Update state to track current agent
        if hasattr(context.session, 'userdata') and context.session.userdata:
            context.session.userdata.current_agent = "daily_planning"
            context.session.userdata.current_context = "planning"

        # Return the DailyPlanningAgent - this triggers the handoff
        return self.daily_planning_agent, "Switching to daily planning mode. Let me start your comprehensive planning session."

    async def on_user_turn_completed(self, turn_ctx: ChatContext, new_message: ChatMessage) -> None:
        """Gate control utterances and normalize user text before the LLM sees it."""
        raw_text = new_message.text_content or ""

        # 1) Ignore empty input
        if not raw_text.strip():
            raise StopResponse()

        # 2) Handle deactivation phrases immediately
        if self._is_deactivation(raw_text):
            self.session.interrupt()
            user_data = getattr(self.session, "userdata", None)
            if user_data is not None:
                user_data.zeno_active = False  # type: ignore[attr-defined]
            raise StopResponse()

        # 3) Determine current activation state
        user_data = getattr(self.session, "userdata", None)
        assistant_is_active = bool(user_data and getattr(user_data, "zeno_active", False))

        # 4) Support one-shot commands while idle (no persistent activation)
        if not assistant_is_active:
            one_shot_tail = self._extract_one_shot(raw_text)
            if one_shot_tail is not None:
                new_message.content = [one_shot_tail]
                return

        # 5) Handle activation phrases (arms assistant, no immediate reply)
        if self._is_activation(raw_text):
            if user_data is not None:
                user_data.zeno_active = True  # type: ignore[attr-defined]
            raise StopResponse()

        # 6) If still idle (and not a one-shot), do nothing this turn
        if not assistant_is_active:
            raise StopResponse()

        # 7) While active, strip vocative prefix before passing to LLM
        stripped_text = self._maybe_strip_zeno_prefix(raw_text)
        if stripped_text != raw_text:
            new_message.content = [stripped_text]


async def entrypoint(ctx: agents.JobContext):
    """
    Enhanced entrypoint for Zeno agent with daily planning capabilities.
    """
    settings = get_settings()
    
    # Check if this is an outbound call by looking for phone_number in metadata
    phone_number = None
    call_purpose = "general"
    try:
        if ctx.job.metadata:
            dial_info = json.loads(ctx.job.metadata)
            phone_number = dial_info.get("phone_number")
            call_purpose = dial_info.get("purpose", "general")
    except (json.JSONDecodeError, KeyError):
        # No metadata or invalid format - assume inbound call
        pass

    print(f"Zeno agent starting for room: {ctx.room.name}")
    print(f"Call purpose: {call_purpose}")
    print(f"Current participants: {len(ctx.room.remote_participants)}")
    
    # Don't target specific participant initially - let the agent handle any participant
    target_identity: Optional[str] = None

    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="en"),
        llm=openai.LLM(model="gpt-5"),
        tts=deepgram.TTS(model="aura-2-thalia-en"),
        vad=silero.VAD.load(),
        turn_detection="vad",
        max_tool_steps=settings.agent_max_tool_steps,
        preemptive_generation=settings.agent_preemptive_generation,
        allow_interruptions=settings.agent_allow_interruptions,
        userdata=ZenoState(),
    )

    # Handle participant events for dynamic targeting
    @ctx.room.on("participant_connected")
    def on_participant_connected(participant):
        print(f"Participant {participant.identity} connected")
        # Reset assistant state for new participants
        if hasattr(session, 'userdata') and session.userdata:
            session.userdata.zeno_active = False

    @ctx.room.on("participant_disconnected")
    def on_participant_disconnected(participant):
        print(f"Participant {participant.identity} disconnected")
        # Reset assistant state when participants disconnect
        if hasattr(session, 'userdata') and session.userdata:
            session.userdata.zeno_active = False
        # Handle cleanup with enhanced Zeno features
        try:
            handle_call_end(session, participant)
        except Exception as e:
            print(f"Error in handle_call_end: {e}")

    # Build room input options
    room_options = RoomInputOptions(
        # Enhanced noise cancellation for better voice quality
        noise_cancellation=noise_cancellation.BVCTelephony(),
    )
    
    # Only set participant_identity if we have a target
    if target_identity is not None:
        room_options.participant_identity = target_identity

    await session.start(
        room=ctx.room,
        agent=ZenoAgent(),
        room_input_options=room_options,
    )

    # Customize greeting based on call purpose
    if phone_number is None:
        # Inbound call - standard greeting
        await session.generate_reply(
            instructions="Greet the user as Zeno, your daily planning assistant, and offer your assistance."
        )
    else:
        # Outbound call - purpose-specific greeting
        if call_purpose == "briefing":
            await session.generate_reply(
                instructions="Greet the user warmly and let them know you're calling to provide their daily briefing. Ask if now is a good time."
            )
        elif call_purpose == "reminder":
            await session.generate_reply(
                instructions="Greet the user and mention you're calling with a scheduled reminder or update."
            )
        else:
            await session.generate_reply(
                instructions="Greet the user and let them know you're calling to check in on their day."
            )


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(
        entrypoint_fnc=entrypoint,

        # agent_name is required for explicit dispatch
        agent_name="my-telephony-agent"
    ))
