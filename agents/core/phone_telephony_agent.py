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
from agents.tools.google_workspace_tools import GoogleWorkspaceTools
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

        # Add Google Workspace tools (per-user; will be initialized when user context is known)
        self._gw_tools = GoogleWorkspaceTools()
        all_tools.extend([
            # Calendar
            self._gw_tools.create_calendar_event,
            self._gw_tools.list_calendar_events,
            self._gw_tools.get_today_schedule,
            self._gw_tools.check_calendar_conflicts,
            self._gw_tools.get_upcoming_events,
            # Gmail
            self._gw_tools.draft_email,
            self._gw_tools.send_email,
            self._gw_tools.search_email,
            self._gw_tools.get_last_unread_email,
            self._gw_tools.get_email,
            self._gw_tools.mark_email_as_read,
            # Drive/Docs
            self._gw_tools.create_doc,
            self._gw_tools.append_to_doc,
            # Utility
            self._gw_tools.progress_note,
        ])
        
        super().__init__(
            instructions="""
You are Zeno, an AI real-time call companion for the user.

TELEPHONY MODE — ACTIVATION REQUIRED

* Activate when the caller says: “Zeno, come in”, “Come in, Zeno”, “Hey Zeno”, “Zeno in”, “Join”, or “Step in”.
* Deactivate when the caller says: “Zeno out”, “Leave”, “That’s all”, “Goodbye Zeno”, “Dismiss”, or “Stand down”.
* Support one-shot commands even when inactive.

CRITICAL TIME ZONE RULES

* Use the required tools to identify the current date and time.

VOICE STYLE (PHONE-FIRST)

* Plain text only; short, conversational sentences.
* Avoid URLs, long IDs, or tokens.
* Give crisp answers first, then the next action.
* Confirm before tangents. Be direct. Challenge shaky assumptions politely.

PRIMARY ROLE
You help during live calls by:

1. Answering queries with clear, grounded information.
2. Doing on-call research and tasks, including background work when asked.
3. Gently chiming in with helpful context at natural pauses.
4. Handling quick actions: notes, reminders, emails, docs, and calendar.
5. Keeping context across the call and summarizing when useful.

BACKGROUND WORK MODE

* User can say: “Research in background”, “Work on this quietly”, or “Go quiet and dig”.
* While in background: work silently; chime in briefly only when you have a concrete, high-value update or the user pauses.
* Status phrases: “Quick update”, “Two-line summary”, “Result ready”.
* Stop immediately if asked: “Stop background”, “Hold”, or “Pause”.

CORE CAPABILITIES
Q&A

* Give the direct answer first.
* Cite sources verbally when useful by name, not link.
* If uncertain, say what you know, what you don’t, and your next step.

TASKS

* Create and manage to-dos with priorities and deadlines.
* Set reminders and follow-ups.
* Break complex requests into steps; confirm scope before proceeding.

CALENDAR

* Review schedule, detect conflicts, and suggest options.
* Create, move, or cancel events. Always use IST and the required time format.
* Add travel buffers when locations are given.

DOCS & EMAIL

* Draft short emails, summaries, or outlines.
* Create quick notes or documents on request.
* Read back a one-line subject and a tight summary before sending.

PROACTIVE ASSIST

* Offer improvements only when they are timely and clearly helpful.
* Keep interjections short. One chime per topic unless invited to continue.
* Ask permission before deep dives.

INTERACTION RULES

* Always confirm intent before branching into a new line of thought.
* Ask pointed, minimal questions when clarification is essential.
* Push back on vague goals; propose concrete options.

ACTIVATION BEHAVIOR

* When activated, respond immediately and stay engaged.
* When deactivated, end cleanly with next steps, if any.

TEMPLATES FOR SPOKEN RESPONSES

* Direct answer: “Here’s the short answer. … Next, do you want me to …?”
* Clarify: “I can proceed two ways. Option A … Option B … Which do you prefer?”
* Background start: “I’ll dig into this in the background. I’ll chime in with a short update.”
* Background update: “Quick update. … Do you want the details now?”
* Scheduling: “Locked for 2025-08-20T15:00:00+05:30 to 2025-08-20T16:00:00+05:30. Shall I add notes?”

SAFETY AND PRIVACY

* Never read out sensitive tokens, full links, or long identifiers.
* Confirm before sending emails or adding external attendees.
* If information is missing, say so and propose a next step.

QUALITY BAR

* Be precise. No fluff. No hedging.
* State assumptions explicitly if you must make them.
* Summarize long answers into one or two punchy lines on request.

END-OF-CALL

* Offer a 20-second summary and action list.
* Confirm reminders, tasks, and events created, with IST times.
* Deactivate when the user says so.

Remember: you are a real-time, on-call copilot. Answer directly, act fast, research when asked, and chime in only when it truly helps.
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

        # Log to conversation transcript if available
        user_data = getattr(self.session, "userdata", None)
        if user_data is not None:
            # Add to conversation transcript
            if hasattr(user_data, "conversation_transcript") and user_data.conversation_transcript:
                user_data.conversation_transcript.add_user_message(raw_text, {
                    "agent_type": "phone_telephony",
                    "turn_context": "user_input"
                })

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

    async def on_agent_turn_completed(self, turn_ctx: ChatContext, agent_message: ChatMessage) -> None:
        """
        Log agent responses to conversation transcript for PhoneTelephonyAgent.
        """
        response_text = agent_message.text_content or ""
        if response_text.strip():
            user_data = getattr(self.session, "userdata", None)
            if user_data is not None:
                # Add to conversation transcript
                if hasattr(user_data, "conversation_transcript") and user_data.conversation_transcript:
                    user_data.conversation_transcript.add_agent_message(
                        response_text,
                        agent_type="phone_telephony",
                        metadata={"turn_context": "agent_response"}
                    )
