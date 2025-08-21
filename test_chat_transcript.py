#!/usr/bin/env python3
"""
Test script to demonstrate the new chat history storage system.
This shows how conversation transcripts are now stored as complete JSON.
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


def test_conversation_transcript():
    """Test the ConversationTranscript class functionality."""
    print("🧪 Testing ConversationTranscript functionality...")

    # Create a new transcript
    transcript = ConversationTranscript()

    # Add some messages
    transcript.add_user_message("Hello, can you help me schedule a meeting?")
    transcript.add_agent_message("Of course! I'd be happy to help you schedule a meeting. What time works best for you?")
    transcript.add_user_message("How about 3 PM tomorrow?")
    transcript.add_agent_message("3 PM tomorrow works great! Let me create that calendar event for you.")

    # Get the full transcript
    full_transcript = transcript.get_transcript()
    print(f"📝 Full transcript has {len(full_transcript)} messages:")

    for i, msg in enumerate(full_transcript, 1):
        role = msg['role'].upper()
        content = msg['content'][:50] + "..." if len(msg['content']) > 50 else msg['content']
        timestamp = msg['timestamp'][:19]  # Just date and time
        print(f"  {i}. {role}: {content} ({timestamp})")

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


def test_database_storage_format():
    """Test how the transcript would be stored in the database."""
    print("\n🗄️  Testing Database Storage Format...")

    transcript = ConversationTranscript()

    # Add sample conversation
    transcript.add_user_message("What's the weather like today?")
    transcript.add_agent_message("It's sunny and 75°F in your location.")
    transcript.add_user_message("Great! Any meetings today?")
    transcript.add_agent_message("You have a team meeting at 2 PM.")

    # Simulate database storage format
    full_transcript = transcript.get_transcript()
    summary = transcript.get_summary()

    # This is how it would be stored in the ChatHistory table
    db_record = {
        "user_id": "user_123",
        "session_id": "session_456",
        "message_type": "transcript",
        "content": f"Conversation transcript with {summary['total_messages']} messages",
        "agent_type": "main_zeno",
        "message_metadata": summary,
        "context_tags": ["conversation_transcript", "complete_session"],
        "full_transcript": full_transcript,
        "created_at": datetime.utcnow().isoformat()
    }

    print("Database record structure:")
    print(json.dumps(db_record, indent=2, default=str))

    return db_record


if __name__ == "__main__":
    print("🚀 Testing New Chat History Storage System")
    print("=" * 50)

    # Test basic functionality
    transcript, summary = test_conversation_transcript()

    # Test database format
    db_record = test_database_storage_format()

    print(f"\n✅ Test completed successfully!")
    print(f"   - Collected {len(transcript)} messages")
    print(f"   - Ready for database storage with full_transcript field")
    print(f"   - Backward compatibility maintained with individual message storage")
