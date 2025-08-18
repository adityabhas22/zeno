"""
Google Gmail Integration for Zeno

Enhanced email management with daily planning features.
"""

from __future__ import annotations

import base64
import re
from email.message import EmailMessage
from typing import Iterable, Optional, List, Dict, Any

from .oauth import get_service

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


class GmailService:
    """Gmail service with Zeno-specific enhancements."""
    
    def __init__(self):
        self.service = get_service("gmail", "v1", GMAIL_SCOPES)
    
    def _build_message(
        self, 
        *, 
        to: Iterable[str], 
        subject: str, 
        body: str, 
        cc: Optional[Iterable[str]] = None
    ) -> EmailMessage:
        """Build email message."""
        msg = EmailMessage()
        msg["To"] = ", ".join(to)
        if cc:
            msg["Cc"] = ", ".join(cc)
        msg["Subject"] = subject
        msg.set_content(body)
        return msg

    def _parse_headers(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Parse email headers."""
        headers = {h.get("name"): h.get("value") for h in payload.get("headers", [])}
        return {
            "from": headers.get("From"),
            "subject": headers.get("Subject"),
            "date": headers.get("Date"),
            "to": headers.get("To"),
            "cc": headers.get("Cc"),
        }

    def draft_email(
        self,
        *,
        to: Iterable[str],
        subject: str,
        body: str,
        cc: Optional[Iterable[str]] = None,
    ) -> Dict[str, Any]:
        """Create an email draft."""
        msg = self._build_message(to=to, subject=subject, body=body, cc=cc)
        encoded = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        
        draft = (
            self.service.users()
            .drafts()
            .create(userId="me", body={"message": {"raw": encoded}})
            .execute()
        )
        
        return {
            "id": draft.get("id"), 
            "messageId": draft.get("message", {}).get("id")
        }

    def send_email(
        self,
        *,
        to: Optional[Iterable[str]] = None,
        subject: Optional[str] = None,
        body: Optional[str] = None,
        cc: Optional[Iterable[str]] = None,
        draft_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send an email."""
        if draft_id:
            sent = (
                self.service.users()
                .drafts()
                .send(userId="me", body={"id": draft_id})
                .execute()
            )
        else:
            assert to and subject and body
            msg = self._build_message(to=to, subject=subject, body=body, cc=cc)
            encoded = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            sent = (
                self.service.users()
                .messages()
                .send(userId="me", body={"raw": encoded})
                .execute()
            )
        
        return {"id": sent.get("id")}

    def search_email(
        self, 
        *, 
        query: str, 
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Search emails using Gmail query syntax."""
        res = (
            self.service.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_results)
            .execute()
        )
        
        ids = [m.get("id") for m in res.get("messages", [])]
        emails = []
        
        for mid in ids:
            m = (
                self.service.users()
                .messages()
                .get(
                    userId="me", 
                    id=mid, 
                    format="metadata", 
                    metadataHeaders=["From", "Subject", "Date", "To", "Cc"]
                )
                .execute()
            )
            
            meta = self._parse_headers(m.get("payload", {}))
            emails.append({
                "id": m.get("id"),
                "snippet": m.get("snippet"),
                "from": meta.get("from"),
                "subject": meta.get("subject"),
                "date": meta.get("date"),
            })
        
        return emails

    def _to_gmail_query(self, natural: str) -> str:
        """Convert natural language to Gmail query."""
        s = natural.lower().strip()
        parts: List[str] = []

        # Basic heuristics
        if "unread" in s or "last" in s or "recent" in s:
            parts.append("is:unread")

        # from: name or email
        m = re.search(r"from\s+([\w_.+-]+@[\w.-]+|[a-zA-Z]+)", s)
        if m:
            sender = m.group(1)
            parts.append(f"from:{sender}")

        # subject keywords
        m = re.search(r"subject\s+([\w\s-]+)", s)
        if m:
            subj = m.group(1).strip()
            parts.append(f"subject:{subj}")

        # general keywords after 'about' / 'regarding'
        m = re.search(r"(?:about|regarding|re)\s+([\w\s-]+)", s)
        if m:
            kw = m.group(1).strip()
            parts.append(kw)

        # recency
        if "today" in s:
            parts.append("newer_than:1d")
        elif "yesterday" in s:
            parts.append("newer_than:2d")
        elif "last week" in s or "past week" in s:
            parts.append("newer_than:7d")

        if not parts:
            parts.append(s)  # fallback to full-text search
        
        return " ".join(parts)

    def search_email_natural(
        self, 
        *, 
        natural_query: str, 
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Search emails using natural language."""
        return self.search_email(
            query=self._to_gmail_query(natural_query), 
            max_results=max_results
        )

    def get_last_unread_email(self) -> Optional[Dict[str, Any]]:
        """Get the most recent unread email."""
        res = (
            self.service.users()
            .messages()
            .list(userId="me", q="is:unread", maxResults=1)
            .execute()
        )
        
        msgs = res.get("messages", [])
        if not msgs:
            return None
        
        mid = msgs[0]["id"]
        m = (
            self.service.users()
            .messages()
            .get(
                userId="me", 
                id=mid, 
                format="metadata", 
                metadataHeaders=["From", "Subject", "Date"]
            )
            .execute()
        )
        
        meta = self._parse_headers(m.get("payload", {}))
        return {
            "id": m.get("id"),
            "snippet": m.get("snippet"),
            "from": meta.get("from"),
            "subject": meta.get("subject"),
            "date": meta.get("date"),
        }

    def get_email_by_id(self, message_id: str) -> Dict[str, Any]:
        """Get a specific email by ID with full content."""
        m = self.service.users().messages().get(
            userId="me", id=message_id, format="full"
        ).execute()
        
        meta = self._parse_headers(m.get("payload", {}))

        def _find_plain_text(payload: Dict[str, Any]) -> Optional[str]:
            """Extract plain text from email payload."""
            parts = payload.get("parts", [])
            if not parts:
                body = payload.get("body", {}).get("data")
                if body:
                    try:
                        return base64.urlsafe_b64decode(body).decode(errors="ignore")
                    except Exception:
                        return None
                return None
            
            for p in parts:
                mime = p.get("mimeType")
                if mime == "text/plain":
                    data = p.get("body", {}).get("data")
                    if data:
                        try:
                            return base64.urlsafe_b64decode(data).decode(errors="ignore")
                        except Exception:
                            continue
                # nested
                nested = _find_plain_text(p)
                if nested:
                    return nested
            return None

        text = _find_plain_text(m.get("payload", {})) or m.get("snippet") or ""
        return {
            "id": m.get("id"),
            "from": meta.get("from"),
            "subject": meta.get("subject"),
            "date": meta.get("date"),
            "text": text,
        }

    def mark_as_read(self, message_id: str) -> None:
        """Mark an email as read."""
        self.service.users().messages().modify(
            userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}
        ).execute()
    
    def get_unread_count(self) -> int:
        """Get count of unread emails."""
        res = (
            self.service.users()
            .messages()
            .list(userId="me", q="is:unread", maxResults=1)
            .execute()
        )
        return res.get("resultSizeEstimate", 0)
    
    def get_email_summary_for_briefing(self) -> str:
        """Generate email summary for morning briefing."""
        unread_count = self.get_unread_count()
        
        if unread_count == 0:
            return "You have no unread emails."
        
        last_unread = self.get_last_unread_email()
        
        if unread_count == 1:
            if last_unread:
                sender = last_unread.get("from", "Unknown sender")
                subject = last_unread.get("subject", "No subject")
                return f"You have 1 unread email from {sender}: {subject}"
            else:
                return "You have 1 unread email."
        else:
            if last_unread:
                sender = last_unread.get("from", "Unknown sender")
                subject = last_unread.get("subject", "No subject")
                return (
                    f"You have {unread_count} unread emails. "
                    f"Most recent is from {sender}: {subject}"
                )
            else:
                return f"You have {unread_count} unread emails."
