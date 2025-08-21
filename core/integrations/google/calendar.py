"""
Google Calendar Integration for Zeno

Enhanced calendar management with daily planning features.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable, Optional, List, Dict, Any
import pytz

from .oauth import get_service
from .user_oauth import get_user_service, check_user_has_google_access

CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar"]


class CalendarService:
    """Google Calendar service with Zeno-specific enhancements."""
    
    def __init__(self, user_id: Optional[str] = None):
        """
        Initialize Calendar service.
        
        Args:
            user_id: If provided, use user-specific credentials. 
                    If None, falls back to global credentials.
        """
        self.user_id = user_id
        
        if user_id:
            if not check_user_has_google_access(user_id, CALENDAR_SCOPES):
                raise Exception(
                    f"User {user_id} has not connected their Google account or missing calendar permissions. "
                    "Please connect your Google account in settings."
                )
            self.service = get_user_service(user_id, "calendar", "v3", CALENDAR_SCOPES)
        else:
            # Enforce user-scoped credentials only
            raise RuntimeError(
                "Google Calendar requires user-scoped credentials. No user context provided."
            )
    
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
        # Ensure timezone is included in datetime strings
        start_dt = self._ensure_timezone(start_iso)
        end_dt = self._ensure_timezone(end_iso)
        
        event_body = {
            "summary": title,
            "start": {"dateTime": start_dt},
            "end": {"dateTime": end_dt},
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
        # Ensure timezone is included in datetime strings
        start_dt = self._ensure_timezone(start_iso)
        end_dt = self._ensure_timezone(end_iso)
        
        events = self.list_events(
            time_min_iso=start_dt,
            time_max_iso=end_dt,
            calendar_id=calendar_id,
            max_results=50
        )
        
        # Filter for actual conflicts (overlapping events)
        conflicts = []
        for event in events:
            start_time = event.get("start", {}).get("dateTime")
            end_time = event.get("end", {}).get("dateTime")
            
            if start_time and end_time:
                # Simple overlap check using the timezone-corrected strings
                if (start_time < end_dt and end_time > start_dt):
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
    
    def _ensure_timezone(self, datetime_str: str) -> str:
        """Ensure datetime string has timezone information for Google Calendar API."""
        if not datetime_str:
            return datetime_str
            
        # If it already has timezone info (Z or offset), return as is
        if datetime_str.endswith('Z') or '+' in datetime_str or datetime_str.endswith('+00:00'):
            return datetime_str
            
        # If it's just ISO format without timezone, assume local timezone
        try:
            # Parse the datetime
            dt = datetime.fromisoformat(datetime_str)
            
            # If it's naive (no timezone), assume user's local timezone
            if dt.tzinfo is None:
                # Use user's local timezone (fallback to UTC if needed)
                local_tz = pytz.timezone('America/Los_Angeles')  # Default to PST for now
                dt = local_tz.localize(dt)
            
            # Return in ISO format with timezone
            return dt.isoformat()
            
        except ValueError:
            # If parsing fails, try adding default timezone
            return datetime_str + '-07:00'  # PST offset
