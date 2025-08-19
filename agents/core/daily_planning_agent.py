"""
Daily Planning Agent for Zeno

Specialized agent for daily planning, morning briefings, and task management.
"""

from __future__ import annotations

from typing import Any, Optional, List
from datetime import datetime, date

from livekit.agents import Agent, function_tool, RunContext

from core.integrations.google.calendar import CalendarService
from core.integrations.google.gmail import GmailService
from core.integrations.google.drive import DriveService
from agents.tools.calendar_tools import CalendarTools
from agents.tools.task_tools import TaskTools
from agents.tools.weather_tools import WeatherTools


class DailyPlanningAgent(Agent):
    """
    Specialized agent for daily planning and morning briefings.
    
    This agent focuses on:
    - Morning briefings with calendar, weather, tasks
    - Calendar management and conflict resolution
    - Task planning and prioritization
    - Daily schedule optimization
    """
    
    def __init__(self) -> None:
        # Initialize service tools first so we can reference them in tools list
        self.calendar_tools = CalendarTools()
        self.task_tools = TaskTools()
        self.weather_tools = WeatherTools()
        
        super().__init__(
            instructions="""You are Zeno's Daily Planning specialist, focused on helping users plan and organize their day effectively.

Your core responsibilities:

1. **Morning Briefings**: Provide comprehensive daily overviews including:
   - Today's calendar events with times and locations
   - Weather conditions and any alerts
   - High-priority tasks and deadlines
   - Important emails or notifications
   - Traffic conditions for scheduled commutes

2. **Calendar Management**: Help with:
   - Reviewing today's schedule
   - Checking for conflicts when scheduling new events
   - Suggesting optimal meeting times
   - Planning travel time between appointments
   - Rescheduling conflicting events

3. **Task Planning**: Assist with:
   - Prioritizing daily tasks based on urgency and importance
   - Breaking down large projects into manageable steps
   - Setting realistic daily goals
   - Tracking task completion progress
   - Suggesting time blocks for focused work

4. **Schedule Optimization**: Provide:
   - Suggestions for better time management
   - Identification of scheduling conflicts
   - Recommendations for meeting-free focus time
   - Travel time calculations between appointments

**Communication Style**:
- Be organized and systematic in your briefings
- Prioritize information by importance and urgency
- Provide actionable insights and suggestions
- Ask clarifying questions to understand priorities
- Keep briefings concise but comprehensive

**Interactive Planning Process**:
- Start interactive sessions by asking "What do you have planned today? What do you want to achieve?"
- After their response, ask "What else do you want to accomplish today? Any other priorities?"
- After their final response, create comprehensive planning document and email draft
- Always use aditya@liftoffllc.com as the default email address

**Default Behavior**:
- When activated, automatically start interactive daily planning with comprehensive day brief
- First provide day brief (calendar, emails, weather, tasks), then ask planning questions
- Use start_interactive_daily_planning tool to begin the full workflow

**Agent Coordination**:
- You are a specialized sub-agent focused on daily planning
- When planning tasks are complete or user wants general assistance, return to main Zeno agent
- Announce when tasks are complete and offer to return to main mode

**Morning Briefing Format**:
1. Greeting and date
2. Weather overview
3. Calendar summary (chronological order)
4. Priority tasks and deadlines
5. Email highlights
6. Traffic/commute information
7. Daily planning suggestions

Remember: Your goal is to help users start each day feeling prepared, organized, and in control of their schedule.
""",
            tools=[
                # Task management tools
                self.task_tools.create_task,
                self.task_tools.list_tasks,
                self.task_tools.complete_task,
                self.task_tools.get_priority_tasks,
                self.task_tools.get_today_tasks,
                self.task_tools.update_task_priority,
                self.task_tools.delete_task,
                self.task_tools.get_task_summary,
                self.task_tools.share_tasks_to_doc,
            ]
        )

    async def on_enter(self) -> None:
        """Automatically start interactive daily planning when agent is activated."""
        await self.session.generate_reply(
            instructions="You've just been activated for daily planning. Use the start_interactive_daily_planning tool to begin the comprehensive planning workflow."
        )

    @function_tool()
    async def generate_morning_briefing(
        self,
        context: RunContext,
        target_date: Optional[str] = None,
        include_weather: bool = True,
        include_traffic: bool = False,
        location: str = "current",
    ) -> dict[str, Any]:
        """Generate a comprehensive morning briefing for the specified date.

        Args:
            target_date: Date for briefing (ISO format, defaults to today)
            include_weather: Include weather information
            include_traffic: Include traffic information
            location: Location for weather/traffic (defaults to user location)
        Returns:
            Complete morning briefing data
        """
        if not target_date:
            target_date = date.today().isoformat()
        
        briefing_data: dict[str, Any] = {
            "date": target_date,
            "generated_at": datetime.now().isoformat(),
            "location": location
        }
        
        # Get calendar information
        try:
            calendar_info = await self.calendar_tools.get_today_schedule(context)
            briefing_data["calendar"] = calendar_info
        except Exception as e:
            briefing_data["calendar"] = {"error": str(e)}
        
        # Get task information
        try:
            priority_tasks = await self.task_tools.get_priority_tasks(context)
            today_tasks = await self.task_tools.get_today_tasks(context)
            briefing_data["tasks"] = {
                "priority": priority_tasks,
                "due_today": today_tasks
            }
        except Exception as e:
            briefing_data["tasks"] = {"error": str(e)}
        
        # Get weather information
        if include_weather:
            try:
                weather_summary = await self.weather_tools.get_weather_summary_for_briefing(
                    context, location
                )
                weather_data = await self.weather_tools.get_current_weather(context, location)
                briefing_data["weather"] = {
                    "summary": weather_summary,
                    "data": weather_data
                }
            except Exception as e:
                briefing_data["weather"] = {"error": str(e)}
        
        # Get email summary
        try:
            gmail_service = GmailService()
            email_summary = gmail_service.get_email_summary_for_briefing()
            briefing_data["email"] = {"summary": email_summary}
        except Exception as e:
            briefing_data["email"] = {"error": str(e)}
        
        return briefing_data

    async def format_briefing_for_voice(
        self,
        context: RunContext,
        briefing_data: dict[str, Any],
    ) -> str:
        """Format briefing data into a voice-friendly narrative.

        Args:
            briefing_data: Raw briefing data from generate_morning_briefing
        Returns:
            Formatted briefing text for voice delivery
        """
        try:
            # Parse the date
            briefing_date = briefing_data.get("date", "today")
            if briefing_date != "today":
                try:
                    parsed_date = datetime.fromisoformat(briefing_date)
                    date_str = parsed_date.strftime("%A, %B %d")
                except:
                    date_str = briefing_date
            else:
                date_str = "today"
            
            briefing_parts = [
                f"Good morning! Here's your briefing for {date_str}."
            ]
            
            # Weather section
            weather = briefing_data.get("weather", {})
            if "summary" in weather and "error" not in weather:
                briefing_parts.append(f"Weather: {weather['summary']}")
            
            # Calendar section
            calendar = briefing_data.get("calendar", {})
            if "summary" in calendar and "error" not in calendar:
                briefing_parts.append(f"Schedule: {calendar['summary']}")
            elif calendar.get("total_events", 0) == 0:
                briefing_parts.append("You have no scheduled events today.")
            
            # Tasks section
            tasks = briefing_data.get("tasks", {})
            if "priority" in tasks and "error" not in tasks:
                priority_tasks = tasks["priority"].get("priority_tasks", [])
                if priority_tasks:
                    task_names = [task["title"] for task in priority_tasks[:3]]
                    if len(task_names) == 1:
                        briefing_parts.append(f"Priority task: {task_names[0]}")
                    else:
                        briefing_parts.append(f"Priority tasks: {', '.join(task_names[:-1])} and {task_names[-1]}")
            
            # Email section
            email = briefing_data.get("email", {})
            if "summary" in email and "error" not in email:
                briefing_parts.append(f"Email: {email['summary']}")
            
            # Closing
            briefing_parts.append("Have a productive day! Let me know if you need help with anything.")
            
            return " ".join(briefing_parts)
            
        except Exception as e:
            return f"I apologize, but I encountered an error generating your briefing: {str(e)}"

    @function_tool()
    async def deliver_morning_briefing(
        self,
        context: RunContext,
        target_date: Optional[str] = None,
        location: str = "current",
    ) -> None:
        """Generate and deliver a complete morning briefing via voice.

        Args:
            target_date: Date for briefing (defaults to today)
            location: Location for weather/traffic information
        """
        # Generate the briefing data
        briefing_data = await self.generate_morning_briefing(
            context, target_date, True, False, location
        )
        
        # Format for voice delivery
        briefing_text = await self.format_briefing_for_voice(context, briefing_data)
        
        # Deliver via voice
        await context.session.say(briefing_text, allow_interruptions=True)

    @function_tool()
    async def check_schedule_conflicts(
        self,
        context: RunContext,
        start_time: str,
        end_time: str,
    ) -> dict[str, Any]:
        """Check for scheduling conflicts when planning new events.

        Args:
            start_time: Start time in ISO format
            end_time: End time in ISO format
        Returns:
            Conflict analysis and suggestions
        """
        return await self.calendar_tools.check_calendar_conflicts(
            context, start_time, end_time
        )

    @function_tool()
    async def suggest_optimal_meeting_time(
        self,
        context: RunContext,
        duration_minutes: int,
        preferred_day: Optional[str] = None,
        time_preferences: str = "business_hours",
    ) -> dict[str, Any]:
        """Suggest optimal times for scheduling new meetings.

        Args:
            duration_minutes: Meeting duration in minutes
            preferred_day: Preferred day (ISO date format)
            time_preferences: "morning", "afternoon", "business_hours", or "flexible"
        Returns:
            Suggested meeting times with conflict analysis
        """
        # This is a placeholder for more advanced scheduling logic
        # In a full implementation, this would analyze calendar patterns,
        # travel time between meetings, and user preferences
        
        return {
            "duration_minutes": duration_minutes,
            "preferred_day": preferred_day,
            "time_preferences": time_preferences,
            "suggested_times": [
                {
                    "start_time": "2025-01-01T10:00:00",
                    "end_time": "2025-01-01T11:00:00",
                    "reason": "No conflicts, optimal focus time"
                }
            ],
            "analysis": "Based on your current schedule, I found several available slots."
        }

    @function_tool()
    async def plan_daily_tasks(
        self,
        context: RunContext,
        available_hours: int = 6,
        focus_time_blocks: bool = True,
    ) -> dict[str, Any]:
        """Help plan and prioritize daily tasks based on available time.

        Args:
            available_hours: Hours available for task work
            focus_time_blocks: Whether to suggest dedicated focus time blocks
        Returns:
            Daily task plan with time allocation suggestions
        """
        # Get current tasks
        all_tasks = await self.task_tools.list_tasks(context, completed=False)
        priority_tasks = await self.task_tools.get_priority_tasks(context)
        
        # Simple task planning logic
        planned_tasks = []
        total_estimated_hours = 0
        
        for task in priority_tasks.get("priority_tasks", [])[:5]:
            # Estimate time based on priority and complexity
            estimated_hours = 2 if task.get("priority", 5) <= 2 else 1
            if total_estimated_hours + estimated_hours <= available_hours:
                planned_tasks.append({
                    **task,
                    "estimated_hours": estimated_hours,
                    "suggested_time_block": f"{total_estimated_hours}h - {total_estimated_hours + estimated_hours}h"
                })
                total_estimated_hours += estimated_hours
        
        return {
            "available_hours": available_hours,
            "planned_tasks": planned_tasks,
            "total_planned_hours": total_estimated_hours,
            "remaining_hours": available_hours - total_estimated_hours,
            "focus_time_blocks": focus_time_blocks,
            "recommendations": [
                "Start with highest priority tasks when energy is highest",
                "Block calendar time for focused work",
                "Take breaks between major tasks"
            ]
        }

    @function_tool()
    async def return_to_main_agent(
        self,
        context: RunContext,
        reason: str = "Daily planning task completed",
    ) -> tuple:
        """Return to the main Zeno agent.

        Args:
            reason: Reason for returning to main agent
        Returns:
            The main ZenoAgent (triggers agent handoff)
        """
        # Import here to avoid circular imports
        from agents.core.zeno_agent import ZenoAgent
        
        # Update state to track current agent
        if hasattr(context.session, 'userdata') and context.session.userdata:
            context.session.userdata.current_agent = "zeno"
            context.session.userdata.current_context = "general"
        
        # Return the main agent with a message - this triggers the handoff
        return ZenoAgent(), "Daily planning session complete. Returning to main Zeno mode. How else can I help you?"

    async def _create_comprehensive_day_brief(self, briefing_data: dict) -> str:
        """Create a comprehensive spoken day brief from briefing data."""
        try:
            # Parse the date
            briefing_date = briefing_data.get("date", "today")
            if briefing_date != "today":
                try:
                    parsed_date = datetime.fromisoformat(briefing_date)
                    day_name = parsed_date.strftime("%A")
                    date_str = parsed_date.strftime("%B %d")
                except:
                    day_name = "today"
                    date_str = briefing_date
            else:
                now = datetime.now()
                day_name = now.strftime("%A")
                date_str = now.strftime("%B %d")
            
            brief_parts = [
                f"Here's your day brief for {day_name}, {date_str}:"
            ]
            
            # Weather section
            weather = briefing_data.get("weather", {})
            if "summary" in weather and "error" not in weather:
                brief_parts.append(f"Weather: {weather['summary']}")
            elif weather.get("data", {}).get("temperature"):
                temp = weather["data"]["temperature"]
                brief_parts.append(f"Current temperature is {temp} degrees.")
            
            # Calendar section - most important part
            calendar = briefing_data.get("calendar", {})
            if "events" in calendar and calendar["events"]:
                event_count = len(calendar["events"])
                if event_count == 1:
                    brief_parts.append("You have 1 event scheduled today:")
                else:
                    brief_parts.append(f"You have {event_count} events scheduled today:")
                
                for event in calendar["events"][:5]:  # Limit to first 5 events
                    title = event.get("summary", "Untitled Event")
                    start_time = event.get("start", {}).get("dateTime", "")
                    location = event.get("location", "")
                    
                    # Format time
                    if start_time:
                        try:
                            dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                            time_str = dt.strftime("%I:%M %p")
                            if time_str.startswith("0"):
                                time_str = time_str[1:]  # Remove leading zero
                        except:
                            time_str = "Time TBD"
                    else:
                        time_str = "All day"
                    
                    event_line = f"At {time_str}: {title}"
                    if location:
                        event_line += f" at {location}"
                    
                    brief_parts.append(event_line)
            else:
                brief_parts.append("You have no scheduled events today.")
            
            # Email section
            email = briefing_data.get("email", {})
            if "summary" in email and "error" not in email and email["summary"]:
                brief_parts.append(f"Emails: {email['summary']}")
            
            # Tasks section
            tasks = briefing_data.get("tasks", {})
            if "priority" in tasks and "error" not in tasks:
                priority_tasks = tasks["priority"].get("priority_tasks", [])
                if priority_tasks:
                    if len(priority_tasks) == 1:
                        brief_parts.append(f"You have 1 high-priority task: {priority_tasks[0]['title']}")
                    else:
                        task_titles = [task["title"] for task in priority_tasks[:3]]
                        if len(task_titles) <= 3:
                            brief_parts.append(f"Your high-priority tasks are: {', '.join(task_titles[:-1])} and {task_titles[-1]}")
                        else:
                            brief_parts.append(f"You have {len(priority_tasks)} high-priority tasks, including {', '.join(task_titles[:2])} and others")
            
            # Today's tasks due
            today_tasks = tasks.get("due_today", {}).get("today_tasks", [])
            if today_tasks:
                brief_parts.append(f"You have {len(today_tasks)} tasks due today.")
            
            # Closing transition - keep it simple
            brief_parts.append("That's your brief.")
            
            return " ".join(brief_parts)
            
        except Exception as e:
            return f"I had trouble generating your day brief: {str(e)}. Let me know if you'd like me to try again."

    @function_tool()
    async def give_day_brief(
        self,
        context: RunContext,
    ) -> str:
        """Provide a comprehensive day briefing with calendar, emails, weather, and tasks.

        Returns:
            Complete day briefing delivered via voice
        """
        try:
            # Generate comprehensive day brief
            today = date.today().isoformat()
            briefing_data = await self.generate_morning_briefing(context, today)
            day_brief = await self._create_comprehensive_day_brief(briefing_data)
            
            # Deliver via voice
            await context.session.say(day_brief, allow_interruptions=True)
            
            return "Day brief delivered successfully."
            
        except Exception as e:
            error_msg = f"I had trouble generating your day brief: {str(e)}"
            await context.session.say(error_msg, allow_interruptions=True)
            return error_msg

    @function_tool()
    async def start_interactive_daily_planning(
        self,
        context: RunContext,
        user_email: str = "aditya@liftoffllc.com",
    ) -> dict[str, Any]:
        """Start an interactive daily planning session with comprehensive day brief first.

        Args:
            user_email: Email address to send the planning summary to
        Returns:
            Result of the planning session
        """
        # Announce what you're doing
        await context.session.say(
            "Perfect! Let me give you your day brief first, then we'll plan together.",
            allow_interruptions=True
        )
        
        # Generate and deliver comprehensive day brief
        today = date.today().isoformat()
        briefing_data = await self.generate_morning_briefing(context, today)
        day_brief = await self._create_comprehensive_day_brief(briefing_data)
        
        await context.session.say(day_brief, allow_interruptions=True)
        
        # Simple planning question
        await context.session.say(
            "Now, what do you want to achieve today?",
            allow_interruptions=True
        )
        
        # Store the session state
        planning_session = {
            "step": "initial_question",
            "user_email": user_email,
            "responses": [],
            "session_id": datetime.now().isoformat(),
            "day_brief_delivered": True,
            "briefing_data": briefing_data
        }
        
        # Store in session userdata for continuation
        if hasattr(context.session, 'userdata') and context.session.userdata:
            context.session.userdata.planning_session = planning_session
        
        return {
            "status": "started",
            "message": "Day brief delivered, interactive planning session started.",
            "session_id": planning_session["session_id"]
        }

    @function_tool()
    async def capture_planning_response(
        self,
        context: RunContext,
        user_response: str,
        is_final_response: bool = False,
    ) -> dict[str, Any]:
        """Capture user's response during interactive planning session.

        Args:
            user_response: What the user wants to achieve/has planned
            is_final_response: Whether this is their final response
        Returns:
            Next step in the planning process
        """
        # Get planning session from session userdata
        planning_session = {}
        if hasattr(context.session, 'userdata') and context.session.userdata:
            planning_session = getattr(context.session.userdata, 'planning_session', {})
        
        if not planning_session:
            return {
                "error": "No active planning session. Please start one first.",
                "action": "start_session"
            }
        
        # Store the response
        planning_session["responses"].append({
            "response": user_response,
            "timestamp": datetime.now().isoformat()
        })
        
        if planning_session.get("step") == "initial_question" and not is_final_response:
            # Ask the follow-up question
            planning_session["step"] = "follow_up"
            await context.session.say(
                "Got it! Anything else you want to add for today?",
                allow_interruptions=True
            )
            
            return {
                "status": "continuing",
                "message": "Follow-up question asked. Waiting for additional items.",
                "step": "follow_up"
            }
        else:
            # Final response received, complete the planning
            return await self.complete_planning_session(context)

    @function_tool()
    async def complete_planning_session(
        self,
        context: RunContext,
    ) -> dict[str, Any]:
        """Complete the interactive planning session and create documents.

        Returns:
            Complete result with created documents and email draft
        """
        # Get planning session from session userdata
        planning_session = {}
        if hasattr(context.session, 'userdata') and context.session.userdata:
            planning_session = getattr(context.session.userdata, 'planning_session', {})
        
        if not planning_session or not planning_session.get("responses"):
            return {
                "error": "No planning session data found",
                "action": "start_new_session"
            }
        
        await context.session.say(
            "Perfect! Let me create your daily planning document and draft an email summary for you.",
            allow_interruptions=True
        )
        
        # Compile all responses
        all_goals = []
        for response in planning_session["responses"]:
            all_goals.append(response["response"])
        
        combined_goals = "\n\n".join([f"• {goal}" for goal in all_goals])
        
        # Generate morning briefing data
        today = date.today().isoformat()
        briefing_data = await self.generate_morning_briefing(context, today)
        
        # Create comprehensive daily planning document
        try:
            drive_service = DriveService()
            planning_doc = self._create_daily_planning_doc(
                drive_service, today, combined_goals, briefing_data
            )
            
            # Draft email
            email_draft = self._create_email_draft(
                planning_session["user_email"], 
                today, 
                combined_goals, 
                planning_doc["url"]
            )
            
            # Send success message
            await context.session.say(
                f"All done! I've created your daily planning document and drafted an email summary. "
                f"Your planning document is available at: {planning_doc['url']}",
                allow_interruptions=True
            )
            
            return {
                "status": "completed",
                "planning_document": planning_doc,
                "email_draft": email_draft,
                "user_goals": all_goals,
                "message": "Daily planning session completed successfully!"
            }
            
        except Exception as e:
            return {
                "status": "error", 
                "error": str(e),
                "message": f"Failed to complete planning session: {str(e)}"
            }

    def _create_daily_planning_doc(
        self, 
        drive_service: DriveService, 
        date: str, 
        user_goals: str, 
        briefing_data: dict
    ) -> dict[str, Any]:
        """Create a comprehensive daily planning document."""
        title = f"Daily Planning - {date}"
        
        content = f"""DAILY PLANNING SESSION
Date: {date}
Generated: {datetime.now().strftime('%I:%M %p')}

WHAT I WANT TO ACHIEVE TODAY:
{user_goals}

MORNING BRIEFING:
====================

"""
        
        # Add weather if available
        weather = briefing_data.get("weather", {})
        if "summary" in weather and "error" not in weather:
            content += f"WEATHER: {weather['summary']}\n\n"
        
        # Add calendar
        calendar = briefing_data.get("calendar", {})
        if "events" in calendar and calendar["events"]:
            content += "TODAY'S SCHEDULE:\n"
            for event in calendar["events"]:
                title = event.get("summary", "Untitled Event")
                start_time = event.get("start", {}).get("dateTime", "")
                if start_time:
                    try:
                        dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                        time_str = dt.strftime("%I:%M %p")
                    except:
                        time_str = "Time TBD"
                else:
                    time_str = "All day"
                content += f"• {time_str}: {title}\n"
            content += "\n"
        else:
            content += "TODAY'S SCHEDULE: No scheduled events\n\n"
        
        # Add tasks
        tasks = briefing_data.get("tasks", {})
        if "priority" in tasks and tasks["priority"].get("priority_tasks"):
            content += "PRIORITY TASKS:\n"
            for task in tasks["priority"]["priority_tasks"]:
                priority_label = "🔴" if task.get("priority") == 1 else "🟡" if task.get("priority") == 2 else "🔵"
                content += f"• {priority_label} {task['title']}\n"
            content += "\n"
        
        content += """
NOTES & REFLECTIONS:
(Space for additional thoughts, ideas, or adjustments throughout the day)


---
Generated by Zeno AI Assistant
"""
        
        return drive_service.create_doc(title=title, initial_text=content)

    def _create_email_draft(
        self, 
        recipient: str, 
        date: str, 
        user_goals: str, 
        doc_url: str
    ) -> dict[str, Any]:
        """Create an email draft with the daily planning summary."""
        subject = f"Daily Planning Summary - {date}"
        
        body = f"""Hi Aditya,

Here's your daily planning summary for {date}:

WHAT YOU WANT TO ACHIEVE TODAY:
{user_goals}

Your complete daily planning document with morning briefing, schedule, and tasks is available here:
{doc_url}

Have a productive day!

Best,
Zeno AI Assistant
"""
        
        # Try to use Gmail service to create draft
        try:
            gmail_service = GmailService()
            draft_result = gmail_service.draft_email(
                to=[recipient],
                subject=subject,
                body=body
            )
            return {
                "status": "draft_created",
                "recipient": recipient,
                "subject": subject,
                "body": body,
                "draft_id": draft_result.get("id"),
                "message": "Email draft created in Gmail"
            }
        except Exception as e:
            # If Gmail service fails, return the draft content
            return {
                "status": "draft_prepared",
                "recipient": recipient,
                "subject": subject,
                "body": body,
                "error": str(e),
                "message": "Email draft prepared but not sent to Gmail (you can copy and send manually)"
            }
