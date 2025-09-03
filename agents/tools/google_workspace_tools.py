"""
Google Workspace Tools Aggregator (Per-User Scoped)

Provides a unified, per-user set of tools for Calendar, Gmail, and Drive/Docs.
Initialize with a Clerk `user_id` when available to enable API calls. If user
context is missing, tool calls will return a clear error instructing to connect
Google or wait for initialization.
"""

from __future__ import annotations

from typing import Any, Iterable, Optional, List

from livekit.agents import function_tool, RunContext

from core.integrations.google.calendar import CalendarService
from core.integrations.google.gmail import GmailService
from core.integrations.google.drive import DriveService


class GoogleWorkspaceTools:
    """Unified Google Workspace tools, scoped to a specific user when initialized."""

    def __init__(self, user_id: Optional[str] = None) -> None:
        self.user_id = user_id
        self.calendar_service: Optional[CalendarService] = None
        self.gmail_service: Optional[GmailService] = None
        self.drive_service: Optional[DriveService] = None

        if user_id:
            self._init_services(user_id)

    def _init_services(self, user_id: str) -> None:
        """Initialize per-user services; tolerate partial failures."""
        self.user_id = user_id
        try:
            self.calendar_service = CalendarService(user_id=user_id)
        except Exception as e:
            self.calendar_service = None
            print(f"⚠️ CalendarService init failed for user {user_id}: {e}")
        try:
            self.gmail_service = GmailService(user_id=user_id)
        except Exception as e:
            self.gmail_service = None
            print(f"⚠️ GmailService init failed for user {user_id}: {e}")
        try:
            self.drive_service = DriveService(user_id=user_id)
        except Exception as e:
            self.drive_service = None
            print(f"⚠️ DriveService init failed for user {user_id}: {e}")

    def initialize_with_user(self, user_id: str) -> None:
        """Initialize per-user services once the user context is known."""
        self._init_services(user_id)

    # ----------------------
    # Calendar Tools
    # ----------------------
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
        if not self.calendar_service:
            return {"error": "Calendar not connected", "message": "Connect Google Calendar in settings."}
        try:
            return self.calendar_service.create_event(
                title=title,
                start_iso=start_iso,
                end_iso=end_iso,
                attendees_emails=attendees_emails,
                location=location,
                description=description,
            )
        except Exception as e:
            return {"error": str(e), "message": "Failed to create calendar event"}

    @function_tool()
    async def list_calendar_events(
        self,
        context: RunContext,
        time_min_iso: Optional[str] = None,
        time_max_iso: Optional[str] = None,
        query: Optional[str] = None,
        max_results: int = 10,
    ) -> List[dict[str, Any]]:
        if not self.calendar_service:
            return []
        try:
            return self.calendar_service.list_events(
                time_min_iso=time_min_iso,
                time_max_iso=time_max_iso,
                query=query,
                max_results=max_results,
            )
        except Exception:
            return []

    @function_tool()
    async def get_today_schedule(self, context: RunContext) -> dict[str, Any]:
        if not self.calendar_service:
            return {"events": [], "summary": "Calendar not connected", "total_events": 0}
        try:
            events = self.calendar_service.get_today_events()
            summary = self.calendar_service.get_calendar_summary()
            return {"events": events, "summary": summary, "total_events": len(events)}
        except Exception as e:
            return {"events": [], "summary": f"Calendar unavailable: {e}", "total_events": 0}

    @function_tool()
    async def check_calendar_conflicts(
        self,
        context: RunContext,
        start_iso: str,
        end_iso: str,
    ) -> dict[str, Any]:
        if not self.calendar_service:
            return {"error": "Calendar not connected"}
        try:
            conflicts = self.calendar_service.check_conflicts(start_iso, end_iso)
            return {"has_conflicts": len(conflicts) > 0, "conflicts": conflicts, "conflict_count": len(conflicts)}
        except Exception as e:
            return {"error": str(e), "message": "Failed to check conflicts"}

    @function_tool()
    async def get_upcoming_events(
        self,
        context: RunContext,
        hours: int = 24,
    ) -> dict[str, Any]:
        if not self.calendar_service:
            return {"events": [], "total_events": 0, "time_span_hours": hours}
        try:
            events = self.calendar_service.get_upcoming_events(hours=hours)
            return {"events": events, "total_events": len(events), "time_span_hours": hours}
        except Exception:
            return {"events": [], "total_events": 0, "time_span_hours": hours}

    # ----------------------
    # Gmail Tools
    # ----------------------
    @function_tool()
    async def draft_email(
        self,
        context: RunContext,
        to: List[str],
        subject: str,
        body: str,
        cc: Optional[List[str]] = None,
    ) -> dict[str, Any]:
        if not self.gmail_service:
            return {"error": "Gmail not connected", "message": "Connect Gmail in settings."}
        try:
            return self.gmail_service.draft_email(to=to, subject=subject, body=body, cc=cc)
        except Exception as e:
            return {"error": str(e), "message": "Failed to create email draft"}

    @function_tool()
    async def send_email(
        self,
        context: RunContext,
        draft_id: Optional[str] = None,
        to: Optional[List[str]] = None,
        subject: Optional[str] = None,
        body: Optional[str] = None,
        cc: Optional[List[str]] = None,
    ) -> dict[str, Any]:
        if not self.gmail_service:
            return {"error": "Gmail not connected"}
        try:
            return self.gmail_service.send_email(draft_id=draft_id, to=to, subject=subject, body=body, cc=cc)
        except Exception as e:
            return {"error": str(e), "message": "Failed to send email"}

    @function_tool()
    async def search_email(
        self,
        context: RunContext,
        query: str,
        max_results: int = 10,
    ) -> List[dict[str, Any]]:
        if not self.gmail_service:
            return []
        try:
            # Natural vs raw Gmail query heuristic: if it contains ':' treat as raw
            if ":" in query:
                return self.gmail_service.search_email(query=query, max_results=max_results)
            return self.gmail_service.search_email_natural(natural_query=query, max_results=max_results)
        except Exception:
            return []

    @function_tool()
    async def get_last_unread_email(self, context: RunContext) -> dict[str, Any] | None:
        if not self.gmail_service:
            return None
        try:
            return self.gmail_service.get_last_unread_email()
        except Exception:
            return None

    @function_tool()
    async def get_email(self, context: RunContext, message_id: str) -> dict[str, Any]:
        if not self.gmail_service:
            return {"error": "Gmail not connected"}
        try:
            email = self.gmail_service.get_email_by_id(message_id)
            # Compact text for voice-friendly reading
            email["text"] = self._compact_text(email.get("text", ""))
            return email
        except Exception as e:
            return {"error": str(e)}

    @function_tool()
    async def mark_email_as_read(self, context: RunContext, message_id: str) -> dict[str, Any]:
        if not self.gmail_service:
            return {"error": "Gmail not connected"}
        try:
            self.gmail_service.mark_as_read(message_id)
            return {"success": True}
        except Exception as e:
            return {"error": str(e)}

    # ----------------------
    # Drive/Docs Tools
    # ----------------------
    @function_tool()
    async def create_doc(
        self,
        context: RunContext,
        title: str,
        initial_text: Optional[str] = None,
    ) -> dict[str, Any]:
        if not self.drive_service:
            return {"error": "Drive/Docs not connected", "message": "Connect Google Drive in settings."}
        try:
            return self.drive_service.create_doc(title=title, initial_text=initial_text)
        except Exception as e:
            return {"error": str(e), "message": "Failed to create Google Doc"}

    @function_tool()
    async def append_to_doc(
        self,
        context: RunContext,
        doc_id: str,
        text: str,
    ) -> dict[str, Any]:
        if not self.drive_service:
            return {"error": "Drive/Docs not connected"}
        try:
            return self.drive_service.append_to_doc(doc_id=doc_id, text=text)
        except Exception as e:
            return {"error": str(e), "message": "Failed to append to Google Doc"}

    # ----------------------
    # Utility
    # ----------------------
    @function_tool()
    async def progress_note(self, context: RunContext, message: str = "Working on it. One moment.") -> None:
        await context.session.say(message, allow_interruptions=True)

    def _compact_text(self, text: str, max_chars: int = 800) -> str:
        import re
        text = re.sub(r"https?://\S+", "[link]", text)
        text = re.sub(r"[A-Za-z0-9_-]{24,}", "[code]", text)
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) > max_chars:
            return text[: max_chars - 3] + "..."
        return text
