"""
Morning Briefing Workflow for Zeno

Orchestrated workflow for generating and delivering comprehensive morning briefings.
"""

from __future__ import annotations

from typing import Optional, Dict, Any
from datetime import datetime, date

from agents.core.daily_planning_agent import DailyPlanningAgent
from core.integrations.google.drive import DriveService
from core.integrations.google.gmail import GmailService


class MorningBriefingWorkflow:
    """
    Orchestrated workflow for morning briefings.
    
    This workflow coordinates multiple services to create comprehensive
    daily briefings and can save them to Google Docs for reference.
    """
    
    def __init__(self):
        self.planning_agent = DailyPlanningAgent()
        self.drive_service = None  # Lazy-loaded when user context is available
        self.gmail_service = None  # Lazy-loaded when user context is available
        self.user_id = None

    def initialize_services_with_user_context(self, user_id: str):
        """Initialize Google services with user-specific credentials."""
        try:
            from core.integrations.google.drive import DriveService
            from core.integrations.google.gmail import GmailService
            
            self.drive_service = DriveService(user_id=user_id)
            self.gmail_service = GmailService(user_id=user_id)
            self.user_id = user_id
            
            # Also initialize the planning agent's calendar tools
            if hasattr(self.planning_agent, 'initialize_calendar_tools_with_user_context'):
                self.planning_agent.initialize_calendar_tools_with_user_context(user_id)
            
            print(f"✅ MorningBriefingWorkflow services initialized for user: {user_id}")
        except Exception as e:
            print(f"❌ Failed to initialize MorningBriefingWorkflow services for user {user_id}: {e}")
            self.drive_service = None
            self.gmail_service = None

    def _ensure_services(self):
        """Ensure services are available, create fallback services if not."""
        if self.drive_service is None:
            try:
                from core.integrations.google.drive import DriveService
                if self.user_id:
                    self.drive_service = DriveService(user_id=self.user_id)
                else:
                    # Fallback: service without user context (will have limited functionality)
                    print("⚠️  Creating DriveService without user context - functionality will be limited")
                    self.drive_service = DriveService()
            except Exception as e:
                print(f"❌ Failed to create DriveService: {e}")
                
        if self.gmail_service is None:
            try:
                from core.integrations.google.gmail import GmailService
                if self.user_id:
                    self.gmail_service = GmailService(user_id=self.user_id)
                else:
                    # Fallback: service without user context (will have limited functionality)
                    print("⚠️  Creating GmailService without user context - functionality will be limited")
                    self.gmail_service = GmailService()
            except Exception as e:
                print(f"❌ Failed to create GmailService: {e}")
    
    async def generate_comprehensive_briefing(
        self,
        context,
        target_date: Optional[str] = None,
        location: str = "current",
        save_to_docs: bool = False,
        email_briefing: bool = False,
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive morning briefing with all available information.
        
        Args:
            context: Agent run context
            target_date: Date for briefing (defaults to today)
            location: Location for weather/traffic info
            save_to_docs: Whether to save briefing to Google Docs
            email_briefing: Whether to email the briefing
            
        Returns:
            Complete briefing data and metadata
        """
        if not target_date:
            target_date = date.today().isoformat()
        
        # Generate the core briefing data
        briefing_data = await self.planning_agent.generate_morning_briefing(
            context, target_date, True, False, location
        )
        
        # Format for voice delivery
        voice_briefing = await self.planning_agent.format_briefing_for_voice(
            context, briefing_data
        )
        
        # Create detailed text briefing
        detailed_briefing = self._create_detailed_briefing(briefing_data)
        
        result = {
            "briefing_data": briefing_data,
            "voice_briefing": voice_briefing,
            "detailed_briefing": detailed_briefing,
            "target_date": target_date,
            "generated_at": datetime.now().isoformat(),
        }
        
        # Save to Google Docs if requested
        if save_to_docs:
            try:
                self._ensure_services()
                if self.drive_service is not None:
                    doc_result = self.drive_service.create_briefing_doc(
                        target_date, detailed_briefing
                    )
                    result["google_doc"] = doc_result
                else:
                    result["google_doc_error"] = "Drive service not available"
            except Exception as e:
                result["google_doc_error"] = str(e)
        
        # Email briefing if requested
        if email_briefing:
            try:
                # This would require user email configuration
                # For now, just mark as requested
                result["email_requested"] = True
            except Exception as e:
                result["email_error"] = str(e)
        
        return result
    
    def _create_detailed_briefing(self, briefing_data: Dict[str, Any]) -> str:
        """Create a detailed text briefing from the briefing data."""
        target_date = briefing_data.get("date", "today")
        
        # Parse date for formatting
        try:
            if target_date != "today":
                parsed_date = datetime.fromisoformat(target_date)
                date_str = parsed_date.strftime("%A, %B %d, %Y")
            else:
                date_str = datetime.now().strftime("%A, %B %d, %Y")
        except:
            date_str = target_date
        
        briefing_lines = [
            f"ZENO DAILY BRIEFING",
            f"Date: {date_str}",
            f"Generated: {datetime.now().strftime('%I:%M %p')}",
            "",
            "=" * 50,
            ""
        ]
        
        # Weather section
        weather = briefing_data.get("weather", {})
        if "error" not in weather and weather.get("summary"):
            briefing_lines.extend([
                "🌤️  WEATHER",
                "-" * 20,
                weather["summary"],
                ""
            ])
            
            # Add detailed weather data if available
            weather_data = weather.get("data", {})
            if weather_data and "error" not in weather_data:
                temp = weather_data.get("temperature")
                humidity = weather_data.get("humidity")
                wind = weather_data.get("wind_speed")
                
                details = []
                if temp:
                    details.append(f"Temperature: {temp}°F")
                if humidity:
                    details.append(f"Humidity: {humidity}%")
                if wind:
                    details.append(f"Wind: {wind} mph")
                
                if details:
                    briefing_lines.extend(details + [""])
        
        # Calendar section
        calendar = briefing_data.get("calendar", {})
        if "error" not in calendar:
            briefing_lines.extend([
                "📅  TODAY'S SCHEDULE",
                "-" * 20
            ])
            
            events = calendar.get("events", [])
            if events:
                for event in events:
                    title = event.get("summary", "Untitled Event")
                    start_time = event.get("start", {}).get("dateTime", "")
                    location = event.get("location", "")
                    
                    # Format time
                    if start_time:
                        try:
                            dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                            time_str = dt.strftime("%I:%M %p")
                        except:
                            time_str = "Time TBD"
                    else:
                        time_str = "All day"
                    
                    event_line = f"• {time_str}: {title}"
                    if location:
                        event_line += f" @ {location}"
                    
                    briefing_lines.append(event_line)
                briefing_lines.append("")
            else:
                briefing_lines.extend(["No scheduled events today.", ""])
        
        # Tasks section
        tasks = briefing_data.get("tasks", {})
        if "error" not in tasks:
            priority_tasks = tasks.get("priority", {}).get("priority_tasks", [])
            today_tasks = tasks.get("due_today", {}).get("today_tasks", [])
            
            if priority_tasks or today_tasks:
                briefing_lines.extend([
                    "✅  PRIORITY TASKS",
                    "-" * 20
                ])
                
                if priority_tasks:
                    briefing_lines.append("High Priority:")
                    for task in priority_tasks:
                        priority = task.get("priority", 5)
                        priority_label = "🔴" if priority == 1 else "🟡" if priority == 2 else "🟢"
                        briefing_lines.append(f"  {priority_label} {task['title']}")
                        if task.get("description"):
                            briefing_lines.append(f"     {task['description']}")
                    briefing_lines.append("")
                
                if today_tasks:
                    briefing_lines.append("Due Today:")
                    for task in today_tasks:
                        briefing_lines.append(f"  • {task['title']}")
                    briefing_lines.append("")
        
        # Email section
        email = briefing_data.get("email", {})
        if "error" not in email and email.get("summary"):
            briefing_lines.extend([
                "📧  EMAIL SUMMARY",
                "-" * 20,
                email["summary"],
                ""
            ])
        
        # Footer
        briefing_lines.extend([
            "=" * 50,
            "",
            "Generated by Zeno AI Assistant",
            f"Next briefing: {datetime.now().replace(hour=8, minute=0).strftime('%A at %I:%M %p')}"
        ])
        
        return "\n".join(briefing_lines)
    
    async def schedule_morning_briefing(
        self,
        briefing_time: str = "08:00",
        location: str = "current",
        auto_call: bool = False,
    ) -> Dict[str, Any]:
        """
        Schedule a morning briefing for the user.
        
        Args:
            briefing_time: Time for briefing in HH:MM format
            location: Location for weather/traffic info
            auto_call: Whether to automatically call the user
            
        Returns:
            Scheduling confirmation and details
        """
        # This would integrate with the call scheduling system
        # For now, return a placeholder response
        
        return {
            "scheduled": True,
            "briefing_time": briefing_time,
            "location": location,
            "auto_call": auto_call,
            "next_briefing": f"Tomorrow at {briefing_time}",
            "message": f"Morning briefing scheduled for {briefing_time} daily."
        }
    
    async def create_comprehensive_daily_docs(
        self,
        context,
        target_date: Optional[str] = None,
        location: str = "current",
    ) -> Dict[str, Any]:
        """
        Create comprehensive daily planning documents including briefing and tasks.
        
        Args:
            context: Agent run context
            target_date: Date for planning (defaults to today)
            location: Location for weather/traffic info
            
        Returns:
            Complete result with all created documents
        """
        if not target_date:
            from datetime import date
            target_date = date.today().isoformat()
        
        result = {
            "target_date": target_date,
            "created_documents": [],
            "errors": []
        }
        
        # Generate morning briefing and save to docs
        try:
            briefing_result = await self.generate_comprehensive_briefing(
                context, target_date, location, save_to_docs=True
            )
            if "google_doc" in briefing_result:
                result["created_documents"].append({
                    "type": "briefing",
                    "document": briefing_result["google_doc"]
                })
        except Exception as e:
            result["errors"].append(f"Failed to create briefing document: {str(e)}")
        
        # Create task summary document
        try:
            task_tools = self.planning_agent.task_tools
            task_doc_result = await task_tools.share_tasks_to_doc(
                context, include_all_tasks=True
            )
            if task_doc_result.get("success"):
                result["created_documents"].append({
                    "type": "tasks",
                    "document": task_doc_result["document"]
                })
        except Exception as e:
            result["errors"].append(f"Failed to create task document: {str(e)}")
        
        # Summary
        result["summary"] = f"Created {len(result['created_documents'])} documents for {target_date}"
        if result["errors"]:
            result["summary"] += f" with {len(result['errors'])} errors"
        
        return result