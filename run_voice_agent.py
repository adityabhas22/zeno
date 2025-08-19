#!/usr/bin/env python3
"""
Zeno Voice Agent Runner

Simple runner script for testing the Zeno voice agent with LiveKit.
This script helps set up and run the voice agent for development and testing.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from agents.core.zeno_agent import entrypoint
from config.settings import get_settings


def check_environment():
    """Check if all required environment variables are set."""
    required_vars = [
        "LIVEKIT_URL",
        "LIVEKIT_API_KEY", 
        "LIVEKIT_API_SECRET",
        "OPENAI_API_KEY",
        "DEEPGRAM_API_KEY",
        "CARTESIA_API_KEY"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these variables in your .env file or environment.")
        print("See README.md for setup instructions.")
        return False
    
    return True


def check_credentials():
    """Check if Google credentials are available."""
    settings = get_settings()
    client_secrets_path = settings.credentials_dir / "client_secret.json"
    
    if not client_secrets_path.exists():
        print("⚠️  Google Workspace integration not configured:")
        print(f"   Missing: {client_secrets_path}")
        print("   Voice agent will work, but Google features will be limited.")
        print("   Add client_secret.json to enable full functionality.")
        return False
    
    print("✅ Google Workspace credentials found")
    return True


def main():
    """Run the Zeno voice agent."""
    print("🤖 Starting Zeno Voice Agent...")
    print("=" * 50)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Check credentials (warn but don't exit)
    check_credentials()
    
    print("\n🎙️  Zeno is ready for voice interaction!")
    print("   Connect to your LiveKit room to start talking with Zeno")
    print("   Say 'Hey Zeno' or 'Zeno' to activate")
    print("   Say 'Goodbye Zeno' to deactivate")
    print("\n🔧 Agent Features:")
    print("   • Daily planning and briefings")
    print("   • Calendar management")  
    print("   • Task tracking")
    print("   • Weather updates")
    print("   • Google Workspace integration")
    print("\n" + "=" * 50)
    
    try:
        # Run the agent using LiveKit's CLI
        from livekit import agents
        agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
        
    except KeyboardInterrupt:
        print("\n👋 Zeno voice agent stopped by user")
    except Exception as e:
        print(f"❌ Error running voice agent: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
