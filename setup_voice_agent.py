#!/usr/bin/env python3
"""
Zeno Voice Agent Setup Script

Sets up the Zeno voice agent for testing and development.
This script helps configure credentials, environment variables, and dependencies.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Any

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


def create_env_template():
    """Create a .env template file with all required variables."""
    env_template = """# Zeno Voice Agent Configuration
# Copy this file to .env and fill in your actual values

# LiveKit Configuration (Required)
LIVEKIT_URL=wss://your-livekit-server.com
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret

# AI Service APIs (Required)
OPENAI_API_KEY=your_openai_api_key
DEEPGRAM_API_KEY=your_deepgram_api_key
CARTESIA_API_KEY=your_cartesia_api_key

# Google Workspace (Optional but recommended)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8790

# Weather API (Optional)
WEATHER_API_KEY=your_weather_api_key

# Database (Optional - SQLite used by default)
DATABASE_URL=sqlite:///./zeno.db

# User Email for Summaries (Optional)
ZENO_USER_EMAIL=your_email@example.com

# Agent Behavior
AGENT_MAX_TOOL_STEPS=12
AGENT_ALLOW_INTERRUPTIONS=true
AGENT_PREEMPTIVE_GENERATION=false

# Development Settings
DEBUG=false
ENVIRONMENT=development
"""
    
    env_file = PROJECT_ROOT / ".env.template"
    with open(env_file, "w") as f:
        f.write(env_template)
    
    print(f"✅ Created environment template: {env_file}")
    return env_file


def create_credentials_dir():
    """Create credentials directory structure."""
    creds_dir = PROJECT_ROOT / "credentials"
    creds_dir.mkdir(exist_ok=True)
    
    # Create a README in credentials dir
    readme_content = """# Credentials Directory

This directory contains authentication credentials for Zeno.

## Google Workspace Integration

To enable Google Workspace features (calendar, email, docs), add your OAuth credentials:

1. Go to the Google Cloud Console: https://console.cloud.google.com/
2. Create a new project or select an existing one
3. Enable the following APIs:
   - Google Calendar API
   - Gmail API
   - Google Drive API
   - Google Docs API
4. Create OAuth 2.0 credentials (Desktop Application)
5. Download the credentials JSON file
6. Rename it to `client_secret.json` and place it in this directory

## File Structure

```
credentials/
├── README.md (this file)
├── client_secret.json (Google OAuth credentials)
└── token.json (Generated after first authentication)
```

Note: The token.json file will be created automatically after your first authentication.
"""
    
    readme_file = creds_dir / "README.md"
    with open(readme_file, "w") as f:
        f.write(readme_content)
    
    print(f"✅ Created credentials directory: {creds_dir}")
    return creds_dir


def create_logs_dir():
    """Create logs directory structure."""
    logs_dir = PROJECT_ROOT / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # Create subdirectories
    (logs_dir / "transcripts").mkdir(exist_ok=True)
    (logs_dir / "summaries").mkdir(exist_ok=True)
    (logs_dir / "agent").mkdir(exist_ok=True)
    
    print(f"✅ Created logs directory: {logs_dir}")
    return logs_dir


def check_dependencies():
    """Check if required dependencies are installed."""
    print("🔍 Checking dependencies...")
    
    try:
        import livekit
        print("   ✅ LiveKit SDK")
    except ImportError:
        print("   ❌ LiveKit SDK - run: pip install -r requirements.txt")
        return False
    
    try:
        import openai
        print("   ✅ OpenAI")
    except ImportError:
        print("   ❌ OpenAI - run: pip install openai")
        return False
    
    try:
        from google.oauth2.credentials import Credentials
        print("   ✅ Google API Client")
    except ImportError:
        print("   ❌ Google API Client - run: pip install google-auth google-api-python-client")
        return False
    
    return True


def install_requirements():
    """Install requirements if they don't exist."""
    requirements_file = PROJECT_ROOT / "requirements.txt"
    
    if not requirements_file.exists():
        print("❌ requirements.txt not found")
        return False
    
    print("📦 Installing dependencies...")
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
        ], check=True, capture_output=True, text=True)
        print("   ✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Failed to install dependencies: {e}")
        print(f"   Error output: {e.stderr}")
        return False


def validate_livekit_config():
    """Validate LiveKit configuration."""
    print("🔍 Validating LiveKit configuration...")
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    livekit_url = os.getenv("LIVEKIT_URL")
    livekit_key = os.getenv("LIVEKIT_API_KEY")
    livekit_secret = os.getenv("LIVEKIT_API_SECRET")
    
    if not all([livekit_url, livekit_key, livekit_secret]):
        print("   ❌ LiveKit configuration incomplete")
        print("   Please set LIVEKIT_URL, LIVEKIT_API_KEY, and LIVEKIT_API_SECRET")
        return False
    
    print("   ✅ LiveKit configuration found")
    return True


def create_sample_room_script():
    """Create a sample script for testing LiveKit rooms."""
    script_content = '''#!/usr/bin/env python3
"""
Sample LiveKit Room Creator

Creates a test room for Zeno voice agent development.
"""

import asyncio
import os
from livekit import api

async def create_test_room():
    """Create a test room for Zeno."""
    # Load from environment
    url = os.getenv("LIVEKIT_URL")
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    
    if not all([url, api_key, api_secret]):
        print("❌ LiveKit credentials not configured")
        return
    
    # Create room
    room_api = api.LiveKitAPI(url, api_key, api_secret)
    
    room_name = "zeno-test-room"
    try:
        room = await room_api.room.create_room(
            api.CreateRoomRequest(name=room_name, empty_timeout=300, max_participants=2)
        )
        print(f"✅ Created test room: {room.name}")
        print(f"   Room SID: {room.sid}")
        
        # Create participant token
        token = api.AccessToken(api_key, api_secret)
        token.with_identity("user")
        token.with_name("Test User")
        token.with_grants(api.VideoGrants(room_join=True, room=room_name))
        
        jwt_token = token.to_jwt()
        print(f"   User token: {jwt_token}")
        print(f"   Join URL: {url}/room/{room_name}?token={jwt_token}")
        
    except Exception as e:
        print(f"❌ Failed to create room: {e}")

if __name__ == "__main__":
    asyncio.run(create_test_room())
'''
    
    script_file = PROJECT_ROOT / "create_test_room.py"
    with open(script_file, "w") as f:
        f.write(script_content)
    
    # Make executable
    os.chmod(script_file, 0o755)
    
    print(f"✅ Created test room script: {script_file}")
    return script_file


def main():
    """Run the setup process."""
    print("🤖 Zeno Voice Agent Setup")
    print("=" * 40)
    
    # Create directory structure
    create_credentials_dir()
    create_logs_dir()
    
    # Create configuration templates
    env_template = create_env_template()
    
    # Check if .env exists
    env_file = PROJECT_ROOT / ".env"
    if not env_file.exists():
        print(f"\n📋 Next steps:")
        print(f"1. Copy {env_template} to {env_file}")
        print(f"2. Fill in your actual API keys and configuration")
        print(f"3. Add your Google OAuth credentials to credentials/client_secret.json")
        print(f"4. Run: python run_voice_agent.py")
    else:
        print(f"✅ Found existing .env file: {env_file}")
    
    # Install dependencies
    if not check_dependencies():
        print("\n📦 Installing dependencies...")
        if not install_requirements():
            print("❌ Failed to install dependencies. Please run: pip install -r requirements.txt")
            return
    
    # Create test scripts
    create_sample_room_script()
    
    # Final validation
    print("\n🔧 Setup Summary:")
    print("=" * 40)
    
    directories = [
        PROJECT_ROOT / "credentials",
        PROJECT_ROOT / "logs",
        PROJECT_ROOT / "logs" / "transcripts"
    ]
    
    for directory in directories:
        status = "✅" if directory.exists() else "❌"
        print(f"{status} {directory}")
    
    files = [
        PROJECT_ROOT / ".env.template",
        PROJECT_ROOT / "requirements.txt",
        PROJECT_ROOT / "run_voice_agent.py",
        PROJECT_ROOT / "create_test_room.py"
    ]
    
    for file in files:
        status = "✅" if file.exists() else "❌"
        print(f"{status} {file}")
    
    print("\n🚀 Ready to start!")
    print("Next: Configure your .env file and run the voice agent")


if __name__ == "__main__":
    main()
