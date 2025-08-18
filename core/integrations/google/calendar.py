"""
Google Calendar Integration for Zeno

Enhanced calendar management with daily planning features.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable, Optional, List, Dict, Any

from .oauth import get_service

CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar"]


class CalendarService:
    """Google Calendar service with Zeno-specific enhancements."""
    
    def __init__(self):
        self.service = get_service("calendar", "v3", CALENDAR_SCOPES)
    
    def create_event(
        self,
        *,
        title: str,
        start_iso: str,
        end_iso: str,
        attendees_emails: Optional[Iterable[str]] = None,
        location: Optional[str] = None,
        description: Optional[str] = None,
        calendar_id: str = "primary",
    ) -> Dict[str, Any]:
        """Create a calendar event."""
        event_body = {
            "summary": title,
            "start": {"dateTime": start_iso},
            "end": {"dateTime": end_iso},
        }
        
        if attendees_emails:
            event_body["attendees"] = [{"email": e} for e in attendees_emails]
        if location:
            event_body["location"] = location
        if description:
            event_body["description"] = description

        created = self.service.events().insert(
            calendarId=calendar_id, body=event_body
        ).execute()
        
        return {
            "id": created.get("id"),
            "htmlLink": created.get("htmlLink"),
            "summary": created.get("summary"),
            "start": created.get("start"),
            "end": created.get("end"),
        }

    def list_events(
        self,
        *,
        time_min_iso: Optional[str] = None,
        time_max_iso: Optional[str] = None,
        query: Optional[str] = None,
        calendar_id: str = "primary",
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """List calendar events within a time range."""
        kwargs = {
            "calendarId": calendar_id,
            "maxResults": max_results,
            "singleEvents": True,
            "orderBy": "startTime",
        }
        
        if time_min_iso:
            kwargs["timeMin"] = time_min_iso
        if time_max_iso:
            kwargs["timeMax"] = time_max_iso
        if query:
            kwargs["q"] = query

        events_result = self.service.events().list(**kwargs).execute()
        items = events_result.get("items", [])
        
        return [
            {
                "id": item.get("id"),
                "summary": item.get("summary"),
                "start": item.get("start"),
                "end": item.get("end"),
                "htmlLink": item.get("htmlLink"),
                "location": item.get("location"),
                "description": item.get("description"),
                "attendees": item.get("attendees", []),
            }
            for item in items
        ]
    
    def get_today_events(self) -> List[Dict[str, Any]]:
        """Get today's calendar events for morning briefing."""
        today = datetime.now().date()
        start_of_day = datetime.combine(today, datetime.min.time()).isoformat() + "Z"
        end_of_day = datetime.combine(today, datetime.max.time()).isoformat() + "Z"
        
        return self.list_events(
            time_min_iso=start_of_day,
            time_max_iso=end_of_day,
            max_results=50
        )
    
    def get_upcoming_events(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get upcoming events for the next specified hours."""
        now = datetime.now()
        future = now + timedelta(hours=hours)
        
        return self.list_events(
            time_min_iso=now.isoformat() + "Z",
            time_max_iso=future.isoformat() + "Z",
            max_results=20
        )
    
    def check_conflicts(
        self, 
        start_iso: str, 
        end_iso: str, 
        calendar_id: str = "primary"
    ) -> List[Dict[str, Any]]:
        """Check for calendar conflicts in the given time range."""
        events = self.list_events(
            time_min_iso=start_iso,
            time_max_iso=end_iso,
            calendar_id=calendar_id,
            max_results=50
        )
        
        # Filter for actual conflicts (overlapping events)
        conflicts = []
        for event in events:
            start_time = event.get("start", {}).get("dateTime")
            end_time = event.get("end", {}).get("dateTime")
            
            if start_time and end_time:
                # Simple overlap check
                if (start_time < end_iso and end_time > start_iso):
                    conflicts.append(event)
        
        return conflicts
    
    def get_calendar_summary(self) -> str:
        """Generate a summary of today's calendar for morning briefing."""
        events = self.get_today_events()
        
        if not events:
            return "You have no scheduled events today."
        
        summary_parts = [f"You have {len(events)} event{'s' if len(events) != 1 else ''} today:"]
        
        for event in events[:5]:  # Limit to first 5 events
            title = event.get("summary", "Untitled Event")
            start_time = event.get("start", {}).get("dateTime")
            location = event.get("location")
            
            if start_time:
                # Parse and format time
                try:
                    dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                    time_str = dt.strftime("%I:%M %p")
                except:
                    time_str = "Unknown time"
            else:
                time_str = "All day"
            
            event_desc = f"• {time_str}: {title}"
            if location:
                event_desc += f" at {location}"
            
            summary_parts.append(event_desc)
        
        if len(events) > 5:
            summary_parts.append(f"...and {len(events) - 5} more events.")
        
        return "\n".join(summary_parts)
