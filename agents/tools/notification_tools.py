"""
Notification Tools for Zeno Agent

Tools for sending push notifications and managing iOS app integration.
"""

from __future__ import annotations

from typing import Any, Optional, Dict
from datetime import datetime

from livekit.agents import function_tool, RunContext

from config.settings import get_settings


class NotificationTools:
    """Notification and iOS integration tools for Zeno agent."""
    
    def __init__(self):
        self.settings = get_settings()

    @function_tool()
    async def send_push_notification(
        self,
        context: RunContext,
        title: str,
        message: str,
        user_id: Optional[str] = None,
        badge_count: Optional[int] = None,
        custom_data: Optional[Dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Send a push notification to the user's iOS device.

        Args:
            title: Notification title
            message: Notification message body
            user_id: Target user ID (optional)
            badge_count: App badge count to set
            custom_data: Additional data to include
        Returns:
            Notification delivery status
        """
        # Placeholder implementation - replace with actual APNs integration
        if not self.settings.apns_key_id:
            return {
                "error": "Push notifications not configured",
                "message": "Please configure APNs credentials"
            }
        
        # Mock notification sending for now
        notification_data = {
            "title": title,
            "message": message,
            "user_id": user_id,
            "badge_count": badge_count,
            "custom_data": custom_data or {},
            "sent_at": datetime.now().isoformat(),
            "status": "sent"
        }
        
        print(f"📱 Push notification sent: {title} - {message}")
        return notification_data

    @function_tool()
    async def schedule_briefing_reminder(
        self,
        context: RunContext,
        briefing_time: str = "08:00",
        reminder_message: str = "Your daily briefing is ready!",
    ) -> dict[str, Any]:
        """Schedule a push notification reminder for daily briefing.

        Args:
            briefing_time: Time for briefing reminder (HH:MM format)
            reminder_message: Custom reminder message
        Returns:
            Scheduling confirmation
        """
        return await self.send_push_notification(
            context,
            title="Zeno Daily Briefing",
            message=reminder_message,
            custom_data={
                "action": "briefing_reminder",
                "briefing_time": briefing_time,
                "type": "daily_briefing"
            }
        )

    @function_tool()
    async def send_task_reminder(
        self,
        context: RunContext,
        task_title: str,
        due_time: Optional[str] = None,
        priority: int = 3,
    ) -> dict[str, Any]:
        """Send a task reminder notification.

        Args:
            task_title: Title of the task
            due_time: When the task is due (ISO format)
            priority: Task priority (1-5)
        Returns:
            Notification delivery status
        """
        priority_labels = {1: "🔴 Urgent", 2: "🟡 High", 3: "🟢 Normal", 4: "🔵 Low", 5: "⚪ Optional"}
        priority_label = priority_labels.get(priority, "🟢 Normal")
        
        message = f"{priority_label}: {task_title}"
        if due_time:
            try:
                due_dt = datetime.fromisoformat(due_time.replace("Z", "+00:00"))
                message += f" (Due: {due_dt.strftime('%I:%M %p')})"
            except:
                pass
        
        return await self.send_push_notification(
            context,
            title="Task Reminder",
            message=message,
            custom_data={
                "action": "task_reminder",
                "task_title": task_title,
                "due_time": due_time,
                "priority": priority,
                "type": "task"
            }
        )

    @function_tool()
    async def send_calendar_alert(
        self,
        context: RunContext,
        event_title: str,
        start_time: str,
        location: Optional[str] = None,
        minutes_before: int = 15,
    ) -> dict[str, Any]:
        """Send a calendar event reminder notification.

        Args:
            event_title: Title of the calendar event
            start_time: Event start time (ISO format)
            location: Event location
            minutes_before: Minutes before event to send reminder
        Returns:
            Notification delivery status
        """
        try:
            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            time_str = start_dt.strftime("%I:%M %p")
        except:
            time_str = "Unknown time"
        
        message = f"{event_title} starts at {time_str}"
        if location:
            message += f" at {location}"
        
        return await self.send_push_notification(
            context,
            title="Calendar Reminder",
            message=message,
            custom_data={
                "action": "calendar_reminder",
                "event_title": event_title,
                "start_time": start_time,
                "location": location,
                "minutes_before": minutes_before,
                "type": "calendar"
            }
        )

    @function_tool()
    async def notify_briefing_ready(
        self,
        context: RunContext,
        briefing_summary: str,
        has_urgent_tasks: bool = False,
        weather_alert: bool = False,
    ) -> dict[str, Any]:
        """Notify user that their daily briefing is ready.

        Args:
            briefing_summary: Brief summary of the briefing content
            has_urgent_tasks: Whether there are urgent tasks
            weather_alert: Whether there are weather alerts
        Returns:
            Notification delivery status
        """
        title = "Your Daily Briefing is Ready"
        
        if has_urgent_tasks and weather_alert:
            title = "⚠️ Important Daily Briefing"
        elif has_urgent_tasks:
            title = "🔴 Daily Briefing - Urgent Tasks"
        elif weather_alert:
            title = "🌧️ Daily Briefing - Weather Alert"
        
        return await self.send_push_notification(
            context,
            title=title,
            message=briefing_summary,
            custom_data={
                "action": "view_briefing",
                "has_urgent_tasks": has_urgent_tasks,
                "weather_alert": weather_alert,
                "type": "briefing_ready"
            }
        )

    @function_tool()
    async def send_call_notification(
        self,
        context: RunContext,
        call_purpose: str = "general",
        scheduled_time: Optional[str] = None,
    ) -> dict[str, Any]:
        """Send notification about incoming Zeno call.

        Args:
            call_purpose: Purpose of the call (briefing, reminder, general)
            scheduled_time: When the call is scheduled (ISO format)
        Returns:
            Notification delivery status
        """
        purpose_messages = {
            "briefing": "Zeno is calling with your daily briefing",
            "reminder": "Zeno is calling with reminders",
            "general": "Zeno is calling to check in",
        }
        
        message = purpose_messages.get(call_purpose, "Zeno is calling")
        
        if scheduled_time:
            try:
                call_dt = datetime.fromisoformat(scheduled_time.replace("Z", "+00:00"))
                message += f" at {call_dt.strftime('%I:%M %p')}"
            except:
                pass
        
        return await self.send_push_notification(
            context,
            title="Incoming Zeno Call",
            message=message,
            custom_data={
                "action": "incoming_call",
                "call_purpose": call_purpose,
                "scheduled_time": scheduled_time,
                "type": "call"
            }
        )
