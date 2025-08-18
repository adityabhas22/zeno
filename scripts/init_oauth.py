#!/usr/bin/env python3
"""
Initialize Google OAuth for Zeno

Setup Google Workspace authentication for Zeno.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import get_settings
from core.integrations.google.oauth import ensure_credentials


def main():
    """Initialize Google OAuth credentials."""
    print("🔐 Zeno Google OAuth Setup")
    print("=" * 40)
    
    settings = get_settings()
    
    # Check if client_secret.json exists
    client_secrets_path = settings.credentials_dir / "client_secret.json"
    
    if not client_secrets_path.exists():
        print("❌ Google client_secret.json not found")
        print(f"Expected location: {client_secrets_path}")
        print()
        print("To get your client_secret.json:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a new project or select existing project")
        print("3. Enable the following APIs:")
        print("   - Google Calendar API")
        print("   - Gmail API") 
        print("   - Google Drive API")
        print("   - Google Docs API")
        print("   - People API (for contacts)")
        print("4. Go to 'Credentials' → 'Create Credentials' → 'OAuth 2.0 Client IDs'")
        print("5. Choose 'Desktop application'")
        print("6. Download the JSON file and save as client_secret.json")
        print(f"7. Place it at: {client_secrets_path}")
        return
    
    print(f"✅ Found client_secret.json at {client_secrets_path}")
    print()
    
    # Define required scopes
    scopes = [
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/documents",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/contacts",
    ]
    
    print("Required OAuth scopes:")
    for scope in scopes:
        print(f"  - {scope}")
    print()
    
    try:
        print("🌐 Starting OAuth flow...")
        print("This will open your web browser for authentication.")
        print("Please complete the authentication process.")
        print()
        
        credentials = ensure_credentials(scopes)
        
        print("✅ Google OAuth setup completed successfully!")
        print(f"✅ Credentials saved to: {settings.credentials_dir / 'token.json'}")
        print()
        print("Zeno now has access to:")
        print("  📅 Google Calendar")
        print("  📧 Gmail")
        print("  📄 Google Docs")
        print("  📁 Google Drive")
        print("  👥 Google Contacts")
        print()
        print("You can now use Zeno's Google Workspace features!")
        
    except Exception as e:
        print(f"❌ OAuth setup failed: {e}")
        print()
        print("Common issues:")
        print("- Make sure you've enabled the required APIs")
        print("- Check that the redirect URI is configured correctly")
        print("- Ensure the OAuth consent screen is properly configured")
        return


if __name__ == "__main__":
    main()
