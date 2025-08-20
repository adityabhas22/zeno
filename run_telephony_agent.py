#!/usr/bin/env python3
"""
Zeno Telephony Agent Runner

Specific runner for telephony calls that sets the correct agent name for LiveKit dispatch.
This agent includes come in/leave activation features for phone calls.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from agents.core.telephony_entrypoint import telephony_entrypoint
from config.settings import get_settings


def check_environment():
    """Check if all required environment variables are set."""
    required_vars = [
        "LIVEKIT_URL",
        "LIVEKIT_API_KEY", 
        "LIVEKIT_API_SECRET",
        "OPENAI_API_KEY",
        "DEEPGRAM_API_KEY",
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
        print("   Telephony agent will work, but Google features will be limited.")
        print("   Add client_secret.json to enable full functionality.")
        return False
    
    print("✅ Google Workspace credentials found")
    return True


def main():
    """Run the Zeno telephony agent."""
    print("📞 Starting Zeno Telephony Agent...")
    print("=" * 50)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Check credentials (warn but don't exit)
    check_credentials()
    
    print("\n📞 Zeno Telephony Agent Features:")
    print("   • Optimized for phone calls")
    print("   • Come in/leave activation commands")
    print("   • Enhanced telephony noise cancellation")
    print("   • Agent name: my-telephony-agent")
    print("\n🎙️  Activation Commands:")
    print("   • 'Hey Zeno' or 'Come in, Zeno'")
    print("   • 'Join' or 'Step in'")
    print("\n🔇 Deactivation Commands:")
    print("   • 'Zeno out' or 'Leave'")
    print("   • 'That's all' or 'Goodbye Zeno'")
    print("\n🔧 Full Agent Features When Active:")
    print("   • Daily planning and briefings")
    print("   • Calendar management")  
    print("   • Task tracking")
    print("   • Weather updates")
    print("   • Google Workspace integration")
    print("\n" + "=" * 50)
    
    try:
        # Run the telephony agent using LiveKit's CLI
        from livekit import agents
        agents.cli.run_app(agents.WorkerOptions(
            entrypoint_fnc=telephony_entrypoint,
            agent_name="my-telephony-agent"  # Must match dispatch-rule.json
        ))
        
    except KeyboardInterrupt:
        print("\n👋 Zeno telephony agent stopped by user")
    except Exception as e:
        print(f"❌ Error running telephony agent: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
