#!/usr/bin/env python3
"""
Clear all integrations from the database for a fresh start
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from core.storage import session_scope
from sqlalchemy import text


def clear_integrations():
    """Clear all integrations from the database."""
    print("🗑️  Clearing all integrations from database...")

    try:
        with session_scope() as db:
            # Count existing integrations
            result = db.execute(text("SELECT COUNT(*) FROM integrations")).scalar()
            print(f"📊 Found {result} integrations to delete")

            if result > 0:
                # Delete all integrations
                db.execute(text("DELETE FROM integrations"))
                db.commit()
                print("✅ Successfully cleared all integrations")
            else:
                print("ℹ️  No integrations found to clear")

    except Exception as e:
        print(f"❌ Error clearing integrations: {e}")
        sys.exit(1)


if __name__ == "__main__":
    clear_integrations()
