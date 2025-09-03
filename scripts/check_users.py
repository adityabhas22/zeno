#!/usr/bin/env python3
"""
Quick script to check users in the database.
"""

import sys
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.storage import session_scope, User

def main():
    """Check all users in the database."""
    print("Checking users in database...")
    
    with session_scope() as session:
        users = session.query(User).all()
        
        if not users:
            print("❌ No users found in database")
            print("\n💡 To sync users:")
            print("1. Configure Clerk webhooks with ngrok URL")
            print("2. Sign up with new email on frontend")
            return
        
        print(f"✅ Found {len(users)} user(s):")
        print("-" * 50)
        
        for user in users:
            print(f"Clerk ID: {user.clerk_user_id}")
            print(f"Email: {user.email}")
            print(f"Name: {user.first_name} {user.last_name}")
            print(f"Created: {user.created_at}")
            print("-" * 50)

if __name__ == "__main__":
    main()
