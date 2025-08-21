"""
Main Zeno Agent - Always Active Version

The primary agent for Zeno without come in/leave features. 
This agent is always responsive and doesn't require activation phrases.
Used for non-telephony interactions.
"""

import asyncio
import json
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
class MainZenoState:
    """State management for main Zeno agent sessions."""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    timezone: Optional[str] = None
    preferences: dict = field(default_factory=dict)
    session_start_time: Optional[str] = None
    daily_briefing_requested: bool = False
    current_context: str = "general"  # "briefing", "planning", "general"
    current_agent: str = "main_zeno"  # "main_zeno", "daily_planning"
    planning_session: Optional[Dict[str, Any]] = None
    
    # Enhanced context sharing between agents
    last_briefing_data: Optional[Dict[str, Any]] = None
    conversation_history: List[str] = field(default_factory=list)
    current_goals: List[str] = field(default_factory=list)
    created_documents: List[Dict[str, Any]] = field(default_factory=list)
    pending_tasks: List[str] = field(default_factory=list)
    chat_buffer: List[Dict[str, Any]] = field(default_factory=list)
    
    # Agent reference for accessing user-scoped tools
    _agent_ref: Optional[Any] = None

    # Conversation transcript collector (will be set by web_entrypoint)
    conversation_transcript: Optional[Any] = None


class MainZenoAgent(Agent):
    """
    Main Zeno AI Agent - Always Active Version
    
    This agent is always responsive and doesn't require activation phrases.
    Designed for non-telephony interactions where immediate responsiveness is desired.
    
    Features:
    - Daily planning capabilities
    - Morning briefing workflows
    - Task management integration
    - Calendar awareness
    - Always active (no come in/leave commands)
    """
    
    def __init__(self) -> None:
        settings = get_settings()
        
        # Initialize specialized agents and workflows
        self.daily_planning_agent = DailyPlanningAgent()
        self.briefing_workflow = MorningBriefingWorkflow()
        
        # Collect all tools before calling super().__init__
        all_tools = []
        
        # Add Google Workspace tools (will be updated with user context later)
        all_tools.extend(get_workspace_tools())
        
        super().__init__(
            instructions="""You are Zeno, an AI-powered daily planning assistant.

**CRITICAL TIME ZONE INSTRUCTIONS:**
-Use the required tools to get the current time and date


**ALWAYS ACTIVE MODE:**
You are in always-active mode. Respond immediately to all user messages without requiring activation phrases.
There are no "come in" or "leave" commands - you are always ready to help.

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

**Interaction Style**:
- Be conversational but efficient
- Provide clear, actionable information
- Ask clarifying questions when needed
- Maintain context throughout conversations
- Adapt to user preferences and patterns
- Always be ready to respond (no activation needed)

**Agent Switching**:
- When users request detailed daily planning, task management, or morning briefings, use the switch_to_daily_planning tool
- Switch with phrases like "let's plan my day", "help me organize tasks", "give me a day brief", "start interactive planning"
- The daily planning agent automatically provides: day brief → planning questions → document creation
- Day brief includes: calendar events, emails, weather, priority tasks, organized for voice delivery
- The daily planning agent can return to main mode when tasks are complete

Remember: You're here to make daily planning effortless and ensure users start each day prepared and organized.
You are always listening and ready to help - no activation required.
""",
            tools=all_tools,
        )

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
                "user_name": getattr(context.session.userdata, "user_name", "User"),
                "user_email": getattr(context.session.userdata, "user_email", None),
                "user_id": getattr(context.session.userdata, "user_id", None),
                "session_id": getattr(context.session.userdata, "session_id", None),
                "timezone": getattr(context.session.userdata, "timezone", None),
                "preferences": getattr(context.session.userdata, "preferences", {}),
                "conversation_history": context.session.userdata.conversation_history,
                "current_goals": context.session.userdata.current_goals,
                "created_documents": context.session.userdata.created_documents,
                "pending_tasks": context.session.userdata.pending_tasks,
                "last_briefing_available": context.session.userdata.last_briefing_data is not None
            }
        return {"error": "No session context available"}

    def update_tools_with_user_context(self, user_id: str):
        """Update Google workspace tools to use user-specific credentials."""
        print(f"🔧 Updating tools with user-specific credentials for user: {user_id}")
        
        try:
            from agents.tools.calendar_tools import CalendarTools
            
            # Create new user-scoped calendar tools instance
            user_calendar_tools = CalendarTools(user_id=user_id)
            
            # Store user_id for future reference
            self._user_id = user_id
            self._user_calendar_tools = user_calendar_tools
            
            print(f"✅ Successfully created user-scoped calendar tools for user: {user_id}")
            print(f"   Calendar service initialized with user context: {user_calendar_tools.user_id is not None}")
            
        except Exception as e:
            print(f"❌ Error updating tools with user context: {e}")
            # Continue with existing tools if update fails

    async def async_update_tools_with_user_context(self, user_id: str):
        """Update Google workspace tools to use user-specific credentials (async version to avoid blocking STT)."""
        print(f"🔧 Updating tools with user-specific credentials for user: {user_id} (async)")
        
        try:
            from agents.tools.calendar_tools import CalendarTools
            
            # Run tool initialization in executor to avoid blocking the event loop
            import asyncio
            
            def _init_tools():
                return CalendarTools(user_id=user_id)
            
            # Create user-scoped calendar tools instance in background thread
            user_calendar_tools = await asyncio.get_event_loop().run_in_executor(
                None, _init_tools
            )
            
            # Store user_id for future reference
            self._user_id = user_id
            self._user_calendar_tools = user_calendar_tools
            
            # Also initialize calendar tools for the daily planning agent
            if hasattr(self, 'daily_planning_agent') and self.daily_planning_agent:
                self.daily_planning_agent.initialize_calendar_tools_with_user_context(user_id)
            
            # Initialize MorningBriefingWorkflow services with user context
            if hasattr(self, 'briefing_workflow') and self.briefing_workflow is not None:
                if hasattr(self.briefing_workflow, 'initialize_services_with_user_context'):
                    self.briefing_workflow.initialize_services_with_user_context(user_id)
            
            print(f"✅ Successfully created user-scoped calendar tools for user: {user_id} (async)")
            print(f"   Calendar service initialized with user context: {user_calendar_tools.user_id is not None}")
            
        except Exception as e:
            print(f"❌ Error updating tools with user context (async): {e}")
            # Continue with existing tools if update fails

    async def on_user_turn_completed(self, turn_ctx: ChatContext, new_message: ChatMessage) -> None:
        """
        Always active - no gating or activation logic.
        Simply processes all user input immediately.
        """
        raw_text = new_message.text_content or ""

        # Ignore empty input
        if not raw_text.strip():
            from livekit.agents import StopResponse
            raise StopResponse()

        # Collect user message for batch persistence later
        user_data = getattr(self.session, "userdata", None)
        if user_data is not None:
            # Add to chat_buffer for backward compatibility
            if hasattr(user_data, "chat_buffer"):
                user_data.chat_buffer.append({
                    "message_type": "user",
                    "content": raw_text,
                })

            # Add to conversation transcript
            if hasattr(user_data, "conversation_transcript"):
                user_data.conversation_transcript.add_user_message(raw_text)

        # No activation logic - always process the message
        # The agent is always ready to respond
        return

    async def on_agent_turn_started(self, turn_ctx: ChatContext) -> None:
        """
        Called when the agent starts its turn to respond.
        We'll capture the response text after it's generated.
        """
        # Store a reference to capture the response
        user_data = getattr(self.session, "userdata", None)
        if user_data is not None:
            user_data._last_agent_turn_ctx = turn_ctx

    async def on_agent_turn_completed(self, turn_ctx: ChatContext, agent_message: ChatMessage) -> None:
        """
        Called when the agent completes its response.
        Log the agent response to the conversation transcript.
        """
        response_text = agent_message.text_content or ""
        if response_text.strip():
            user_data = getattr(self.session, "userdata", None)
            if user_data is not None:
                # Add to chat_buffer for backward compatibility
                if hasattr(user_data, "chat_buffer"):
                    user_data.chat_buffer.append({
                        "message_type": "agent",
                        "content": response_text,
                    })

                # Add to conversation transcript
                if hasattr(user_data, "conversation_transcript"):
                    user_data.conversation_transcript.add_agent_message(response_text, "main_zeno")
