"""
Google Workspace Agent for Zeno

Enhanced workspace integration agent with all Google Workspace tools.
"""

from __future__ import annotations

from typing import Any, Iterable, Optional, List

from livekit.agents import Agent, function_tool, RunContext

from core.integrations.google.calendar import CalendarService
from core.integrations.google.gmail import GmailService
from core.integrations.google.drive import DriveService


class WorkspaceAgent(Agent):
    """
    Google Workspace integration agent for Zeno.
    
    Provides comprehensive Google Workspace functionality including:
    - Calendar management
    - Email handling
    - Document creation and management
    - Contact lookup
    """
    
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "You are Zeno's Google Workspace specialist. Be concise and direct."
                " Use natural phrasing, avoid reading URLs, IDs or long codes aloud."
                " Prefer summaries and confirmations for better voice interaction."
                " Focus on helping users manage their calendar, email, and documents efficiently."
            ),
        )
        
        # Initialize services
        self.calendar_service = CalendarService()
        self.gmail_service = GmailService()
        self.drive_service = DriveService()

    # Calendar Tools
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
            start_iso: ISO 8601 start datetime (e.g. 2025-08-11T15:00:00-07:00)
            end_iso: ISO 8601 end datetime
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

    # Email Tools
    @function_tool()
    async def draft_email(
        self,
        context: RunContext,
        to: List[str],
        subject: str,
        body: str,
        cc: Optional[List[str]] = None,
    ) -> dict[str, Any]:
        """Create an email draft. Use 'send_email' to send it."""
        return self.gmail_service.draft_email(to=to, subject=subject, body=body, cc=cc)

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
        """Send an email. Either provide a draft_id or to/subject/body (and cc)."""
        return self.gmail_service.send_email(
            draft_id=draft_id, to=to, subject=subject, body=body, cc=cc
        )

    @function_tool()
    async def search_email(
        self, 
        context: RunContext, 
        query: str, 
        max_results: int = 10
    ) -> List[dict[str, Any]]:
        """Search emails using a natural phrase or Gmail query (e.g. 'last unread from Alex', 'subject invoice').

        If the input looks natural, convert it; otherwise use as-is.
        Returns minimal metadata suitable for summarizing over voice.
        """
        # Heuristic: treat as natural if it lacks ':' operators
        if ":" in query:
            return self.gmail_service.search_email(query=query, max_results=max_results)
        return self.gmail_service.search_email_natural(
            natural_query=query, max_results=max_results
        )

    @function_tool()
    async def get_last_unread_email(self, context: RunContext) -> dict[str, Any] | None:
        """Fetch the last unread email's from/subject/snippet for quick summary."""
        return self.gmail_service.get_last_unread_email()

    @function_tool()
    async def get_email(self, context: RunContext, message_id: str) -> dict[str, Any]:
        """Get a specific email by Gmail message ID, returning a voice-friendly text body."""
        email = self.gmail_service.get_email_by_id(message_id)
        # Compact the text to avoid reading long URLs or IDs
        compact = self._compact_text(email.get("text", ""))
        email["text"] = compact
        return email

    @function_tool()
    async def mark_email_as_read(self, context: RunContext, message_id: str) -> None:
        """Mark an email as read by Gmail message ID."""
        self.gmail_service.mark_as_read(message_id)

    # Document Tools
    @function_tool()
    async def create_doc(
        self, 
        context: RunContext, 
        title: str, 
        initial_text: Optional[str] = None
    ) -> dict[str, Any]:
        """Create a Google Doc with an optional initial body of text."""
        return self.drive_service.create_doc(title=title, initial_text=initial_text)

    @function_tool()
    async def append_to_doc(
        self, 
        context: RunContext, 
        doc_id: str, 
        text: str
    ) -> dict[str, Any]:
        """Append plain text to the end of a Google Doc by ID."""
        return self.drive_service.append_to_doc(doc_id=doc_id, text=text)

    # Contact Tools (placeholder - would need People API implementation)
    @function_tool()
    async def lookup_contact(
        self, 
        context: RunContext, 
        name_or_email: str
    ) -> dict[str, Any] | None:
        """Lookup a contact by name or email. Returns the best match or None."""
        # Placeholder implementation
        return {
            "name": name_or_email,
            "email": f"{name_or_email}@example.com" if "@" not in name_or_email else name_or_email,
            "note": "Contact lookup not fully implemented yet"
        }

    @function_tool()
    async def list_contacts(
        self, 
        context: RunContext, 
        page_size: int = 50
    ) -> List[dict[str, Any]]:
        """List contacts from the user's People directory (limited fields)."""
        # Placeholder implementation
        return []

    # Utility Tools
    @function_tool()
    async def progress_note(
        self, 
        context: RunContext, 
        message: str = "Working on it. One moment."
    ) -> None:
        """Politely inform the user we're working on a long task. Keep it brief."""
        await context.session.say(message, allow_interruptions=True)

    def _compact_text(self, text: str, max_chars: int = 800) -> str:
        """Compact text for voice-friendly reading."""
        import re
        # Remove long URLs and tokens
        text = re.sub(r"https?://\S+", "[link]", text)
        text = re.sub(r"[A-Za-z0-9_-]{24,}", "[code]", text)
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) > max_chars:
            return text[: max_chars - 3] + "..."
        return text


def get_workspace_tools() -> List:
    """Export workspace tools for use by other agents."""
    # Create a temporary instance to harvest its decorated tools
    tmp = WorkspaceAgent()
    return list(tmp.tools)
