#!/usr/bin/env python3
"""
Database migration management script for Zeno.

Provides easy commands for managing database migrations with Alembic.
"""

import sys
import argparse
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import logging
from alembic.config import Config
from alembic import command
from sqlalchemy import text
from config.settings import get_settings
from core.storage import db_manager


def get_alembic_config():
    """Get Alembic configuration."""
    alembic_cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    # Set the database URL from settings
    settings = get_settings()
    alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)
    return alembic_cfg


def test_connection():
    """Test database connection."""
    print("Testing database connection...")
    try:
        settings = get_settings()
        print(f"Database URL: {settings.database_url[:50]}...")
        
        with db_manager.get_session() as session:
            result = session.execute(text("SELECT version()"))
            version = result.fetchone()
            print(f"✅ Connected successfully!")
            print(f"PostgreSQL version: {version}")
            return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


def create_migration(message: str, autogenerate: bool = True):
    """Create a new migration."""
    print(f"Creating migration: {message}")
    try:
        alembic_cfg = get_alembic_config()
        if autogenerate:
            command.revision(alembic_cfg, message=message, autogenerate=True)
        else:
            command.revision(alembic_cfg, message=message)
        print("✅ Migration created successfully!")
    except Exception as e:
        print(f"❌ Failed to create migration: {e}")
        sys.exit(1)


def run_migrations():
    """Run all pending migrations."""
    print("Running database migrations...")
    try:
        alembic_cfg = get_alembic_config()
        command.upgrade(alembic_cfg, "head")
        print("✅ Migrations completed successfully!")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)


def show_current_revision():
    """Show current database revision."""
    try:
        alembic_cfg = get_alembic_config()
        command.current(alembic_cfg, verbose=True)
    except Exception as e:
        print(f"❌ Failed to get current revision: {e}")
        sys.exit(1)


def show_migration_history():
    """Show migration history."""
    try:
        alembic_cfg = get_alembic_config()
        command.history(alembic_cfg, verbose=True)
    except Exception as e:
        print(f"❌ Failed to get migration history: {e}")
        sys.exit(1)


def downgrade_migration(target: str = "-1"):
    """Downgrade to a specific migration."""
    print(f"Downgrading to: {target}")
    try:
        alembic_cfg = get_alembic_config()
        command.downgrade(alembic_cfg, target)
        print("✅ Downgrade completed successfully!")
    except Exception as e:
        print(f"❌ Downgrade failed: {e}")
        sys.exit(1)


def main():
    """Main command-line interface."""
    parser = argparse.ArgumentParser(description="Zeno Database Migration Manager")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Test connection
    subparsers.add_parser("test", help="Test database connection")

    # Create migration
    migrate_parser = subparsers.add_parser("create", help="Create a new migration")
    migrate_parser.add_argument("message", help="Migration message")
    migrate_parser.add_argument("--no-autogenerate", action="store_true", 
                               help="Don't auto-generate migration content")

    # Run migrations
    subparsers.add_parser("upgrade", help="Run all pending migrations")

    # Show current revision
    subparsers.add_parser("current", help="Show current database revision")

    # Show history
    subparsers.add_parser("history", help="Show migration history")

    # Downgrade
    downgrade_parser = subparsers.add_parser("downgrade", help="Downgrade database")
    downgrade_parser.add_argument("target", nargs="?", default="-1", 
                                 help="Target revision (default: -1)")

    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(level=logging.INFO)

    if args.command == "test":
        test_connection()
    elif args.command == "create":
        if not test_connection():
            print("Fix database connection before creating migrations.")
            sys.exit(1)
        create_migration(args.message, not args.no_autogenerate)
    elif args.command == "upgrade":
        if not test_connection():
            print("Fix database connection before running migrations.")
            sys.exit(1)
        run_migrations()
    elif args.command == "current":
        show_current_revision()
    elif args.command == "history":
        show_migration_history()
    elif args.command == "downgrade":
        downgrade_migration(args.target)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
