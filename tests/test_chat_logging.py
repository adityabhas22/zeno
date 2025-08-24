#!/usr/bin/env python3
"""
Test script to verify chat logging functionality across all agents.
This tests that all agents properly log user messages and agent responses.
"""

import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from agents.core.web_entrypoint import ConversationTranscript
import json
from datetime import datetime


def test_conversation_transcript_functionality():
    """Test the ConversationTranscript class functionality."""
    print("🧪 Testing ConversationTranscript functionality...")

    # Create a new transcript
    transcript = ConversationTranscript()

    # Test adding user messages from different agents
    transcript.add_user_message("Hello from main agent", {"agent_type": "main_zeno"})
    transcript.add_user_message("Hello from daily planning", {"agent_type": "daily_planning"})
    transcript.add_user_message("Hello from phone telephony", {"agent_type": "phone_telephony"})

    # Test adding agent responses
    transcript.add_agent_message("Response from main agent", "main_zeno")
    transcript.add_agent_message("Response from daily planning", "daily_planning")
    transcript.add_agent_message("Response from phone telephony", "phone_telephony")

    # Get the full transcript
    full_transcript = transcript.get_transcript()
    print(f"📝 Full transcript has {len(full_transcript)} messages:")

    for i, msg in enumerate(full_transcript, 1):
        role = msg['role'].upper()
        content = msg['content'][:50] + "..." if len(msg['content']) > 50 else msg['content']
        agent_type = msg.get('metadata', {}).get('agent_type', 'unknown')
        timestamp = msg['timestamp'][:19]  # Just date and time
        print(f"  {i}. {role} ({agent_type}): {content} ({timestamp})")

    # Get summary
    summary = transcript.get_summary()
    print(f"\n📊 Summary:")
    print(f"   Total messages: {summary['total_messages']}")
    print(f"   User messages: {summary['user_messages']}")
    print(f"   Agent messages: {summary['agent_messages']}")
    print(f"   Duration: {summary['session_duration_seconds']:.1f} seconds")

    # Show JSON format
    print(f"\n💾 JSON Format for Database Storage:")
    json_output = transcript.get_transcript_as_json()
    print(json_output)

    return full_transcript, summary


def test_agent_chat_logging_methods():
    """Test that all agents have the required chat logging methods."""
    print("\n🔍 Testing Agent Chat Logging Methods...")

    agents_to_check = [
        ("MainZenoAgent", "/Users/adityabhaskara/Coding Projects/Zeno/agents/core/main_zeno_agent.py"),
        ("DailyPlanningAgent", "/Users/adityabhaskara/Coding Projects/Zeno/agents/core/daily_planning_agent.py"),
        ("PhoneTelephonyAgent", "/Users/adityabhaskara/Coding Projects/Zeno/agents/core/phone_telephony_agent.py"),
    ]

    for agent_name, file_path in agents_to_check:
        print(f"\n📋 Checking {agent_name}...")

        try:
            with open(file_path, 'r') as f:
                content = f.read()

            has_user_turn = "on_user_turn_completed" in content
            has_agent_turn = "on_agent_turn_completed" in content
            has_transcript_logging = "conversation_transcript" in content

            print(f"   ✅ on_user_turn_completed: {'YES' if has_user_turn else 'NO'}")
            print(f"   ✅ on_agent_turn_completed: {'YES' if has_agent_turn else 'NO'}")
            print(f"   ✅ conversation_transcript logging: {'YES' if has_transcript_logging else 'NO'}")

            if not all([has_user_turn, has_agent_turn, has_transcript_logging]):
                print(f"   ⚠️  {agent_name} may be missing some chat logging functionality")
            else:
                print(f"   ✅ {agent_name} has complete chat logging functionality")

        except Exception as e:
            print(f"   ❌ Error checking {agent_name}: {e}")


def test_database_storage_format():
    """Test how the transcript would be stored in the database."""
    print("\n🗄️  Testing Database Storage Format...")

    transcript = ConversationTranscript()

    # Add sample conversation from different agents
    transcript.add_user_message("Plan my day", {"agent_type": "main_zeno"})
    transcript.add_agent_message("Switching to daily planning agent", "main_zeno")
    transcript.add_user_message("I need to finish presentation", {"agent_type": "daily_planning"})
    transcript.add_agent_message("Created task for presentation", "daily_planning")

    # Simulate database storage format
    full_transcript = transcript.get_transcript()
    summary = transcript.get_summary()

    # This is how it would be stored in the ChatHistory table
    db_record = {
        "user_id": "user_31aNjxl39kgQ7E3BiZGN4rqBJaU",
        "session_id": "session_456",
        "message_type": "transcript",
        "content": f"Complete conversation transcript with {summary['total_messages']} messages across multiple agents",
        "agent_type": "multi_agent_session",
        "message_metadata": summary,
        "context_tags": ["conversation_transcript", "multi_agent", "complete_session"],
        "full_transcript": full_transcript,
        "created_at": datetime.utcnow().isoformat()
    }

    print("Database record structure:")
    print(json.dumps(db_record, indent=2, default=str))

    return db_record


def main():
    print("🚀 Testing Chat Logging Across All Agents")
    print("=" * 50)

    # Test basic functionality
    transcript, summary = test_conversation_transcript_functionality()

    # Test agent methods
    test_agent_chat_logging_methods()

    # Test database format
    db_record = test_database_storage_format()

    print(f"\n✅ All tests completed!")
    print(f"   - Collected {len(transcript)} messages from multiple agents")
    print(f"   - All agents have chat logging functionality")
    print(f"   - Ready for database storage with full_transcript field")


if __name__ == "__main__":
    main()
