#!/usr/bin/env python3
"""
Test script to demonstrate the enhanced goal parsing functionality.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from core.storage.task_operations import TaskOperations
from core.storage.timezone_utils import TimezoneManager
import re

def test_enhanced_parsing():
    """Test the enhanced goal parsing with the user's example."""

    goals_text = """Tasks for tomorrow: 1) Finish presentation for xSpecies AI. 2) Complete research report for xSpecies AI. 3) Finalize marketing plan for Thousand Rupees Hustle Challenge. 4) Find and contact tennis coaches to start lessons. Meeting with xSpecies AI at 2:00 PM."""

    print("Original text:")
    print(goals_text)
    print("\n" + "="*50 + "\n")

    # Simulate the parsing logic
    goals = []
    global_time_info = None
    time_pattern = r'at (\d{1,2}(?::\d{2})?\s*(?:am|pm)?)'
    time_match = re.search(time_pattern, goals_text, re.IGNORECASE)
    if time_match:
        global_time_info = time_match.group(1).strip()
        print(f"Global time info extracted: {global_time_info}")

    # Use a simple approach: split by "number) " pattern
    # This handles the specific format: "1) text 2) text 3) text"

    # Remove the prefix "Tasks for tomorrow: "
    cleaned_text = re.sub(r'^Tasks for tomorrow:\s*', '', goals_text.strip())

    # Split by numbered patterns
    parts = re.split(r'\s*(\d+)\)\s*', cleaned_text)

    print(f"Split parts: {parts}")

    # Extract the actual task texts (skip the numbers)
    for i in range(2, len(parts), 2):
        if i < len(parts):
            task_text = parts[i].strip()
            # Remove any trailing content after the next number or "Meeting"
            task_text = re.split(r'\s*(?=\d+\)|Meeting|at)', task_text)[0].strip()
            if task_text and len(task_text) > 5:
                goals.append(task_text)

    # Also extract the meeting part
    meeting_match = re.search(r'Meeting with ([^.]+?)(?:\s*at|$)', cleaned_text)
    if meeting_match:
        meeting_text = f"Meeting with {meeting_match.group(1).strip()}"
        if meeting_text not in goals:
            goals.append(meeting_text)

    print(f"Goals found: {goals}")

    # Remove duplicates and clean up
    goals = list(dict.fromkeys(goals))  # Remove duplicates while preserving order

    print(f"Parsed {len(goals)} individual tasks:")
    for i, goal in enumerate(goals, 1):
        # Extract time information specific to this goal
        goal_time = None
        time_match = re.search(time_pattern, goal, re.IGNORECASE)
        if time_match:
            goal_time = time_match.group(1).strip()
            goal_clean = re.sub(time_pattern, '', goal, flags=re.IGNORECASE).strip()
        else:
            goal_clean = goal
            goal_time = global_time_info if global_time_info else None

        # Determine priority and category
        priority = 3
        category = "general"
        goal_lower = goal.lower()

        if any(word in goal_lower for word in ['urgent', 'asap', 'critical', 'important', 'deadline']):
            priority = 1
        elif any(word in goal_lower for word in ['soon', 'priority', 'key', 'meeting']):
            priority = 2

        if any(word in goal_lower for word in ['work', 'meeting', 'project', 'call', 'presentation', 'report', 'research']):
            category = "work"
        elif any(word in goal_lower for word in ['health', 'exercise', 'gym', 'run', 'tennis']):
            category = "health"
        elif any(word in goal_lower for word in ['marketing', 'plan', 'challenge', 'hustle']):
            category = "work"

        print(f"{i}. {goal_clean}")
        print(f"   → Category: {category}, Priority: {priority}, Time: {goal_time}")
        print()

if __name__ == "__main__":
    test_enhanced_parsing()
