"""
Phone Telephony Agent - Sub-agent for Telephony Calls

This agent handles telephony calls and includes come in/leave activation features.
Based on the original ZenoAgent but specifically designed for phone interactions.
"""

import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Optional, Any, Dict, Tuple, List
from dataclasses import dataclass, field

# Add project root to Python path to allow imports from any location
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables first
from dotenv import load_dotenv
load_dotenv()

from livekit import agents
from livekit.agents import Agent, AgentSession, StopResponse, ChatContext, ChatMessage, function_tool, RunContext
from livekit.plugins import openai, deepgram, cartesia, silero, noise_cancellation

from config.settings import get_settings
from agents.core.workspace_agent import get_workspace_tools
from agents.core.daily_planning_agent import DailyPlanningAgent
from agents.workflows.morning_briefing import MorningBriefingWorkflow


@dataclass
class PhoneTelephonyState:
    """State management for phone telephony agent sessions."""
    zeno_active: bool = False  # Starts inactive, requires activation
    user_id: Optional[str] = None
    session_start_time: Optional[str] = None
    daily_briefing_requested: bool = False
    current_context: str = "general"
    current_agent: str = "phone_telephony"
    planning_session: Optional[Dict[str, Any]] = None
    
    # Enhanced context sharing between agents
    last_briefing_data: Optional[Dict[str, Any]] = None
    conversation_history: List[str] = field(default_factory=list)
    current_goals: List[str] = field(default_factory=list)
    created_documents: List[Dict[str, Any]] = field(default_factory=list)
    pending_tasks: List[str] = field(default_factory=list)


class PhoneTelephonyAgent(Agent):
    """
    Phone Telephony Agent for Zeno - Sub-agent for Phone Calls
    
    This agent is specifically designed for telephony interactions and includes:
    - Come in/leave activation features
    - Voice-optimized responses for phone calls
    - Telephony-specific noise cancellation
    - All the same capabilities as the main agent when activated
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
        
        super().__init__(
            instructions="""You are Zeno, an AI-powered daily planning assistant optimized for phone calls.

**TELEPHONY MODE - ACTIVATION REQUIRED:**
You are operating in telephony mode. Users must activate you with phrases like:
- "Zeno, come in" or "Come in, Zeno"
- "Hey Zeno" or "Zeno in"
- "Join" or "Step in"

Deactivate with phrases like:
- "Zeno out" or "Leave"
- "That's all" or "Goodbye Zeno"
- "Dismiss" or "Stand down"

**CRITICAL TIME ZONE INSTRUCTIONS:**
- Today's date is August 20, 2025 (Tuesday) in Indian Standard Time (IST, UTC+05:30)
- ALWAYS use IST timezone (+05:30) for all calendar events
- Format calendar event times as: YYYY-MM-DDTHH:mm:ss+05:30
- When users say "today" = 2025-08-20, "tomorrow" = 2025-08-21
- Default event duration is 1 hour unless specified otherwise

**VOICE-OPTIMIZED INSTRUCTIONS:**
You are writing text that will be spoken over a phone call.
- Use plain text only. No Markdown, no emojis. Only basic punctuation.
- Keep sentences short (≈10–20 words) and conversational.
- Avoid reading URLs, IDs, or long tokens aloud.
- Prefer short summaries, confirmations, and next steps.
- Use natural phrasing suitable for voice interaction.

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
   - Provide timely information and updates
   - Offer planning suggestions and optimizations
   - Maintain context throughout conversations

**Interaction Style for Phone Calls**:
- Be conversational but efficient
- Provide clear, actionable information optimized for voice
- Ask clarifying questions when needed
- Maintain context throughout conversations
- Adapt to user preferences and patterns
- Wait for activation before responding to general queries

**Agent Switching**:
- When users request detailed daily planning, task management, or morning briefings, use the switch_to_daily_planning tool
- Switch with phrases like "let's plan my day", "help me organize tasks", "give me a day brief", "start interactive planning"
- The daily planning agent automatically provides: day brief → planning questions → document creation

**Activation Behavior**:
- Respond to "Hey Zeno" or similar activation phrases
- Support one-shot commands even when not actively listening
- Deactivate with "That's all" or "Goodbye Zeno"
- Only respond to general queries when activated

Remember: You're optimized for phone calls with activation control and voice-friendly responses.
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
                "wake",
                "wake up",
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
    async def switch_to_daily_planning(self, context: RunContext) -> Tuple[DailyPlanningAgent, str]:
        """Switch to the specialized daily planning agent."""
        # Update state to track current agent
        if hasattr(context.session, 'userdata') and context.session.userdata:
            context.session.userdata.current_agent = "daily_planning"
            context.session.userdata.current_context = "planning"
            context.session.userdata.conversation_history.append("Switched to daily planning mode")
        
        return self.daily_planning_agent, "Switching to daily planning mode. Let me start your comprehensive planning session."

    @function_tool()
    async def get_session_context(self, context: RunContext) -> dict[str, Any]:
        """Get current session context and conversation state."""
        if hasattr(context.session, 'userdata') and context.session.userdata:
            return {
                "current_agent": context.session.userdata.current_agent,
                "current_context": context.session.userdata.current_context,
                "conversation_history": context.session.userdata.conversation_history,
                "current_goals": context.session.userdata.current_goals,
                "created_documents": context.session.userdata.created_documents,
                "pending_tasks": context.session.userdata.pending_tasks,
                "last_briefing_available": context.session.userdata.last_briefing_data is not None
            }
        return {"error": "No session context available"}

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
