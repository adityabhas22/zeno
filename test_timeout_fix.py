#!/usr/bin/env python3
"""
Test script to verify the Deepgram timeout fix works correctly.

This script tests the timeout handling mechanisms implemented to prevent
Deepgram connection timeouts during long-running tool calls.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from config.settings import get_settings
from agents.tools.task_tools import TaskTools

async def test_timeout_handling():
    """Test the timeout handling mechanisms."""
    print("🧪 Testing Deepgram Timeout Fix")
    print("=" * 50)

    settings = get_settings()

    # Test 1: Verify settings are loaded correctly
    print("✅ Testing Settings Configuration:")
    print(f"   - STT Timeout: {settings.stt_timeout}s")
    print(f"   - LLM Timeout: {settings.llm_timeout}s")
    print(f"   - Tool Call Timeout: {settings.tool_call_timeout}s")
    print(f"   - Session Timeout: {settings.session_timeout}s")
    print(f"   - Progress Note Interval: {settings.progress_note_interval}s")

    # Test 2: Test progress note functionality
    print("\n✅ Testing Progress Note System:")

    # Mock context for testing
    class MockSession:
        def __init__(self):
            self.messages = []

        async def say(self, message, allow_interruptions=True):
            self.messages.append(message)
            print(f"   📣 Progress: {message}")
            return True

    class MockUserdata:
        def __init__(self):
            self.user_id = "test_user_123"

    class MockContext:
        def __init__(self):
            self.session = MockSession()
            self.session.userdata = MockUserdata()

    # Test progress note
    tools = TaskTools()
    context = MockContext()

    try:
        result = await tools.progress_note(context, "Testing progress note system...")
        print(f"   ✅ Progress note sent successfully: {result}")
    except Exception as e:
        print(f"   ❌ Progress note failed: {e}")

    # Test 3: Test timeout wrapper
    print("\n✅ Testing Timeout Wrapper:")

    async def mock_long_operation(delay=2.0):
        """Mock a long-running operation."""
        await asyncio.sleep(delay)
        return {"success": True, "result": "Operation completed"}

    try:
        result = await tools._run_with_progress_and_timeout(
            context,
            mock_long_operation,
            "Test Operation",
            timeout_seconds=5.0,
            progress_message="Running test operation..."
        )
        print(f"   ✅ Timeout wrapper works: {result}")
    except Exception as e:
        print(f"   ❌ Timeout wrapper failed: {e}")

    # Test 4: Test timeout scenario
    print("\n✅ Testing Timeout Scenario:")

    async def mock_very_long_operation(delay=10.0):
        """Mock a very long operation that should timeout."""
        await asyncio.sleep(delay)
        return {"success": True}

    try:
        result = await tools._run_with_progress_and_timeout(
            context,
            mock_very_long_operation,
            "Timeout Test Operation",
            timeout_seconds=3.0,  # Short timeout
            progress_message="This should timeout..."
        )
        print(f"   ❌ Timeout should have occurred: {result}")
    except Exception as e:
        print(f"   ✅ Timeout handled correctly: {str(e)[:50]}...")

    print("\n" + "=" * 50)
    print("🎉 Deepgram Timeout Fix Test Complete!")
    print("\nKey improvements implemented:")
    print("• Progress notes prevent STT timeouts")
    print("• Configurable timeouts for all operations")
    print("• Async timeout handling with proper error recovery")
    print("• Enhanced AgentSession configuration")
    print("\nTo test with actual voice:")
    print("1. Run: python run_voice_agent.py dev")
    print("2. Ask Zeno to 'create a task summary document'")
    print("3. Verify progress messages appear during the operation")

if __name__ == "__main__":
    asyncio.run(test_timeout_handling())
