#!/usr/bin/env python3
"""
Database initialization script for Zeno.

Creates database tables and sets up initial data.
Run this after setting up your .env file with database configuration.
"""

import sys
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import logging
from config.settings import get_settings
from core.storage import init_database, db_manager


def main():
    """Initialize the database."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # Get settings
    settings = get_settings()
    logger.info(f"Initializing database: {settings.database_url}")
    
    try:
        # Initialize database and create tables
        init_database()
        
        # Verify database connection
        with db_manager.get_session() as session:
            # Test query to ensure everything is working
            result = session.execute("SELECT 1")
            assert result.fetchone()[0] == 1
            
        logger.info("✅ Database initialized successfully!")
        logger.info("You can now start using Zeno with multi-user support.")
        
        # Print next steps
        print("\n" + "="*60)
        print("🎉 DATABASE SETUP COMPLETE!")
        print("="*60)
        print("\nNext steps:")
        print("1. Set up Clerk webhooks to sync user data")
        print("2. Configure your integrations (Google Workspace, etc.)")
        print("3. Start the Zeno API server: python api/main.py")
        print("4. Start the voice agent: python run_voice_agent.py")
        print("\nFor Clerk integration, see:")
        print("https://clerk.com/docs/integrations/webhooks")
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
