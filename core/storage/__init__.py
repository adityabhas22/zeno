"""
Storage module for Zeno database operations.

Provides SQLAlchemy models and database session management
for Clerk-authenticated multi-user system.
"""

from .database import (
    DatabaseManager,
    db_manager,
    get_database_session,
    init_database,
    close_database,
    create_session,
    session_scope,
)

from .models import (
    Base,
    User,
    UserSession,
    Briefing,
    Task,
    DailyPlan,
    ChatHistory,
    Document,
    Integration,
    Notification,
    KnowledgeItem,
)

__all__ = [
    # Database management
    "DatabaseManager",
    "db_manager",
    "get_database_session",
    "init_database",
    "close_database",
    "create_session",
    "session_scope",
    
    # Models
    "Base",
    "User",
    "UserSession", 
    "Briefing",
    "Task",
    "DailyPlan",
    "ChatHistory",
    "Document",
    "Integration",
    "Notification",
    "KnowledgeItem",
]
