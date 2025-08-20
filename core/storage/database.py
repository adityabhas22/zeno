"""
Database configuration and session management for Zeno.

Handles SQLAlchemy setup, connection management, and provides
database session utilities for the application.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from config.settings import get_settings
from .models import Base


logger = logging.getLogger(__name__)


class DatabaseManager:
    """Database connection and session management."""
    
    def __init__(self):
        self.settings = get_settings()
        self.engine = None
        self.SessionLocal = None
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database engine and session factory."""
        # Create engine with appropriate configuration
        engine_kwargs: dict = {
            "echo": self.settings.database_echo,
            "future": True,  # Use SQLAlchemy 2.0 style
        }
        
        # Handle SQLite-specific configuration
        if self.settings.database_url.startswith("sqlite"):
            engine_kwargs["poolclass"] = StaticPool
            engine_kwargs["connect_args"] = {"check_same_thread": False}
        
        self.engine = create_engine(self.settings.database_url, **engine_kwargs)
        
        # Set up WAL mode for SQLite for better concurrency
        if self.settings.database_url.startswith("sqlite"):
            @event.listens_for(self.engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA cache_size=10000")
                cursor.execute("PRAGMA temp_store=MEMORY")
                cursor.close()
        
        # Create session factory
        self.SessionLocal = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False,
        )
        
        logger.info(f"Database initialized: {self.settings.database_url}")
    
    def create_tables(self):
        """Create all database tables."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            raise
    
    def drop_tables(self):
        """Drop all database tables (use with caution)."""
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.info("Database tables dropped successfully")
        except Exception as e:
            logger.error(f"Error dropping database tables: {e}")
            raise
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Get a database session with automatic cleanup.
        
        Usage:
            with db_manager.get_session() as session:
                # Use session here
                pass
        """
        if self.SessionLocal is None:
            raise RuntimeError("Database not initialized. Call _initialize_database() first.")
        
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def get_session_sync(self) -> Session:
        """
        Get a database session for manual management.
        
        Note: Remember to close the session when done.
        """
        if self.SessionLocal is None:
            raise RuntimeError("Database not initialized. Call _initialize_database() first.")
        
        return self.SessionLocal()


# Global database manager instance
db_manager = DatabaseManager()


def get_database_session() -> Generator[Session, None, None]:
    """
    Dependency function for FastAPI to get database sessions.
    
    Usage in FastAPI:
        @app.get("/endpoint")
        def endpoint(db: Session = Depends(get_database_session)):
            # Use db session here
            pass
    """
    with db_manager.get_session() as session:
        yield session


def init_database():
    """Initialize database and create tables."""
    logger.info("Initializing database...")
    db_manager.create_tables()
    logger.info("Database initialization complete")


def close_database():
    """Close database connections."""
    if db_manager.engine:
        db_manager.engine.dispose()
        logger.info("Database connections closed")


# Convenience functions for direct use
def create_session() -> Session:
    """Create a new database session."""
    return db_manager.get_session_sync()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """
    Session scope context manager.
    
    Usage:
        with session_scope() as session:
            # Use session here
            pass
    """
    with db_manager.get_session() as session:
        yield session
