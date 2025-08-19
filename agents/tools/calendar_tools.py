"""
Calendar Tools for Zeno Agent

Enhanced calendar management tools with daily planning features.
"""

from __future__ import annotations

from typing import Any, Optional, List
from datetime import datetime, date

from livekit.agents import function_tool, RunContext

from core.integrations.google.calendar import CalendarService
from core.integrations.google.gmail import GmailService
from core.integrations.google.drive import DriveService


class CalendarTools:
    """Calendar management tools for Zeno agent."""
    
    def __init__(self):
        self.calendar_service = CalendarService()
        self.gmail_service = GmailService()
        self.drive_service = DriveService()

    @function_tool()
    async def create_calendar_event(
        self,
        context: RunContext,
        title: str,
        start_iso: str,
        end_iso: str,
        attendees_emails: Optional[List[str]] = None,
        location: Optional[str] = None,
        description: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create a calendar event on the user's primary calendar.

        Args:
            title: Event title
            start_iso: ISO 8601 start datetime (e.g. 2025-08-21T13:00:00 or 2025-08-21T13:00:00-07:00)
                      If no timezone specified, Pacific Time will be assumed
            end_iso: ISO 8601 end datetime (same format as start_iso)
            attendees_emails: List of attendee emails
            location: Optional location
            description: Optional description
        Returns:
            A dictionary with event id and link
        """
        return self.calendar_service.create_event(
            title=title,
            start_iso=start_iso,
            end_iso=end_iso,
            attendees_emails=attendees_emails,
            location=location,
            description=description,
        )

    @function_tool()
    async def list_calendar_events(
        self,
        context: RunContext,
        time_min_iso: Optional[str] = None,
        time_max_iso: Optional[str] = None,
        query: Optional[str] = None,
        max_results: int = 10,
    ) -> List[dict[str, Any]]:
        """List upcoming calendar events within an optional time range or query."""
        return self.calendar_service.list_events(
            time_min_iso=time_min_iso,
            time_max_iso=time_max_iso,
            query=query,
            max_results=max_results,
        )

    @function_tool()
    async def get_today_schedule(
        self,
        context: RunContext,
    ) -> dict[str, Any]:
        """Get today's complete schedule for daily planning and briefings."""
        events = self.calendar_service.get_today_events()
        summary = self.calendar_service.get_calendar_summary()
        
        return {
            "events": events,
            "summary": summary,
            "total_events": len(events)
        }

    @function_tool()
    async def check_calendar_conflicts(
        self,
        context: RunContext,
        start_iso: str,
        end_iso: str,
    ) -> dict[str, Any]:
        """Check for calendar conflicts when scheduling new events.
        
        Args:
            start_iso: ISO 8601 start datetime (e.g. 2025-08-21T13:00:00)
            end_iso: ISO 8601 end datetime
        """
        conflicts = self.calendar_service.check_conflicts(start_iso, end_iso)
        
        return {
            "has_conflicts": len(conflicts) > 0,
            "conflicts": conflicts,
            "conflict_count": len(conflicts)
        }

    @function_tool()
    async def get_upcoming_events(
        self,
        context: RunContext,
        hours: int = 24,
    ) -> dict[str, Any]:
        """Get upcoming events for the next specified hours."""
        events = self.calendar_service.get_upcoming_events(hours=hours)
        
        return {
            "events": events,
            "total_events": len(events),
            "time_span_hours": hours
        }

    @function_tool()
    async def progress_note(
        self, 
        context: RunContext, 
        message: str = "Working on it. One moment."
    ) -> None:
        """Politely inform the user we're working on a long task. Keep it brief."""
        await context.session.say(message, allow_interruptions=True)
