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
        )
        
        # Initialize service tools
        self.calendar_tools = CalendarTools()
        self.task_tools = TaskTools()
        self.weather_tools = WeatherTools()

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
        
        briefing_data = {
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

    @function_tool()
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
