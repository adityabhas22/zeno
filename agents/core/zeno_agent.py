"""
Zeno Agent - Main AI Assistant

The primary agent for Zeno, providing daily planning assistance and voice interaction.
Renamed and enhanced from the original Jarvis implementation.
"""

import asyncio
import json
import re
from typing import Optional
from dataclasses import dataclass

from livekit import agents
from livekit.agents import Agent, AgentSession, StopResponse, RoomInputOptions
from livekit.agents.voice import ChatContext, ChatMessage
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
        
        super().__init__(
            instructions=f"""You are Zeno, an AI-powered daily planning assistant.

Your primary role is to help users plan and organize their day through:

1. **Morning Briefings**: Provide comprehensive daily overviews including:
   - Today's calendar events and schedule
   - Weather and traffic conditions
   - Priority tasks and reminders
   - Important updates or notifications

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

4. **Proactive Communication**: 
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

**Activation**:
- Respond to "Hey Zeno" or "Zeno" for activation
- Support one-shot commands even when not actively listening
- Deactivate with "That's all" or "Goodbye Zeno"

Remember: You're here to make daily planning effortless and ensure users start each day prepared and organized.
""",
            max_tool_steps=settings.agent_max_tool_steps,
            preemptive_generation=settings.agent_preemptive_generation,
            allow_interruptions=settings.agent_allow_interruptions,
        )
        
        # Add Google Workspace tools
        self.tools.extend(get_workspace_tools())
        
        # Add daily planning tools
        self.tools.extend([
            self.daily_planning_agent.generate_morning_briefing,
            self.daily_planning_agent.deliver_morning_briefing,
            self.daily_planning_agent.check_schedule_conflicts,
            self.daily_planning_agent.suggest_optimal_meeting_time,
            self.daily_planning_agent.plan_daily_tasks,
        ])

    def _is_activation(self, text: str) -> bool:
        """Check if text contains Zeno activation phrases."""
        activation_patterns = [
            r"^(?:hey\s+)?zeno\b",
            r"^zeno\b",
            r"\bzeno\s*(?:are\s+you\s+there|wake\s+up|listen)\b"
        ]
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in activation_patterns)

    def _is_deactivation(self, text: str) -> bool:
        """Check if text contains Zeno deactivation phrases."""
        deactivation_patterns = [
            r"\b(?:that'?s\s+all|goodbye|good\s*bye)\s*zeno\b",
            r"\bzeno\s*(?:stop|sleep|deactivate|turn\s+off)\b",
            r"^(?:that'?s\s+all|goodbye|good\s*bye|stop|end|finish)$"
        ]
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in deactivation_patterns)

    def _extract_one_shot(self, text: str) -> Optional[str]:
        """Extract one-shot command if present."""
        one_shot_patterns = [
            r"^(?:hey\s+)?zeno[,\s]+(.+)$",
            r"^zeno[,\s]+(.+)$"
        ]
        
        for pattern in one_shot_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _maybe_strip_zeno_prefix(self, text: str) -> str:
        """Remove Zeno vocative prefix from text."""
        return re.sub(r"^(?:hey\s+)?(?:zeno|zeno)\b\s*", "", text, flags=re.IGNORECASE)

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
            await self.session.generate_reply(
                instructions="Acknowledge the deactivation politely and briefly."
            )
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
            await self.session.generate_reply(
                instructions="Greet the user as Zeno and ask how you can help with their daily planning."
            )
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
        stt=deepgram.STT(model="nova-2", language="en"),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=cartesia.TTS(model="sonic-english", voice="79a125e8-cd45-4c13-8a67-188112f4dd22"),  # Professional voice
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

    await session.start(
        room=ctx.room,
        agent=ZenoAgent(),
        room_input_options=RoomInputOptions(
            # Enhanced noise cancellation for better voice quality
            noise_cancellation=noise_cancellation.BVCTelephony(),
            participant_identity=target_identity,  # None allows any participant
        ),
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
    agents.cli.run_app(entrypoint)
