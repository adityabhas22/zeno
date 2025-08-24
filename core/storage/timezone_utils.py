"""
Timezone utilities for handling date/time operations across the Zeno system.

Ensures consistent timezone handling for tasks, events, and user interactions.
"""

from __future__ import annotations

import logging
from typing import Optional
from datetime import datetime, date, time, timezone as dt_timezone
from dateutil import parser
import pytz

logger = logging.getLogger(__name__)


class TimezoneManager:
    """Manages timezone conversions and operations."""

    # Common timezone mappings
    TIMEZONE_MAP = {
        'IST': 'Asia/Kolkata',
        'EST': 'America/New_York',
        'PST': 'America/Los_Angeles',
        'CST': 'America/Chicago',
        'MST': 'America/Denver',
        'UTC': 'UTC',
        'GMT': 'GMT',
        'JST': 'Asia/Tokyo',
        'CET': 'Europe/Paris',
        'EET': 'Europe/Helsinki',
        'MSK': 'Europe/Moscow',
        'IST': 'Asia/Kolkata',  # Indian Standard Time
        'HKT': 'Asia/Hong_Kong',
        'SGT': 'Asia/Singapore',
        'KST': 'Asia/Seoul',
    }

    @staticmethod
    def normalize_timezone(tz_input: str) -> str:
        """
        Normalize various timezone formats to IANA timezone names.

        Args:
            tz_input: Timezone string (e.g., 'IST', 'Asia/Kolkata', 'UTC+5:30')

        Returns:
            IANA timezone name (e.g., 'Asia/Kolkata')
        """
        if not tz_input:
            return 'UTC'

        # Clean the input
        tz_input = tz_input.strip().upper()

        # Direct mapping
        if tz_input in TimezoneManager.TIMEZONE_MAP:
            return TimezoneManager.TIMEZONE_MAP[tz_input]

        # Handle UTC offset formats
        if tz_input.startswith('UTC'):
            if '+' in tz_input or '-' in tz_input:
                # For now, return UTC and log - could be enhanced to handle specific offsets
                logger.info(f"UTC offset timezone {tz_input} normalized to UTC")
                return 'UTC'
            return 'UTC'

        # Try to find in pytz
        try:
            return str(pytz.timezone(tz_input))
        except pytz.exceptions.UnknownTimeZoneError:
            logger.warning(f"Unknown timezone {tz_input}, defaulting to UTC")
            return 'UTC'

    @staticmethod
    def get_timezone_object(tz_name: str) -> pytz.BaseTzInfo:
        """
        Get pytz timezone object from timezone name.

        Args:
            tz_name: IANA timezone name

        Returns:
            pytz timezone object
        """
        try:
            return pytz.timezone(tz_name)
        except Exception as e:
            logger.error(f"Failed to get timezone object for {tz_name}: {e}")
            return pytz.UTC

    @staticmethod
    def parse_time_with_timezone(
        time_str: str,
        user_timezone: str = 'UTC'
    ) -> tuple[time, str]:
        """
        Parse a time string and return time object with normalized timezone.

        Args:
            time_str: Time string (e.g., '2:30 PM', '14:30', 'morning', 'afternoon')
            user_timezone: User's timezone

        Returns:
            Tuple of (time object, normalized timezone name)
        """
        normalized_tz = TimezoneManager.normalize_timezone(user_timezone)
        tz_obj = TimezoneManager.get_timezone_object(normalized_tz)

        # Handle natural language time references
        time_str_lower = time_str.lower().strip()

        if 'morning' in time_str_lower or 'early' in time_str_lower:
            return time(9, 0), normalized_tz  # 9 AM
        elif 'afternoon' in time_str_lower:
            return time(14, 0), normalized_tz  # 2 PM
        elif 'evening' in time_str_lower or 'night' in time_str_lower:
            return time(18, 0), normalized_tz  # 6 PM
        elif 'lunch' in time_str_lower or 'noon' in time_str_lower:
            return time(12, 0), normalized_tz  # 12 PM
        elif 'breakfast' in time_str_lower:
            return time(8, 0), normalized_tz  # 8 AM
        elif 'dinner' in time_str_lower:
            return time(19, 0), normalized_tz  # 7 PM

        # Parse specific time formats
        try:
            # Handle HH:MM format
            if ':' in time_str:
                time_obj = time.fromisoformat(time_str)
                return time_obj, normalized_tz

            # Handle 12-hour format (e.g., "2:30 PM", "2 PM")
            import re
            match = re.match(r'(\d{1,2}):?(\d{2})?\s*(am|pm)?', time_str_lower)
            if match:
                hour = int(match.group(1))
                minute = int(match.group(2)) if match.group(2) else 0
                am_pm = match.group(3)

                # Convert to 24-hour format
                if am_pm == 'pm' and hour != 12:
                    hour += 12
                elif am_pm == 'am' and hour == 12:
                    hour = 0

                return time(hour, minute), normalized_tz

        except (ValueError, AttributeError) as e:
            logger.warning(f"Failed to parse time '{time_str}': {e}")

        # Default to 9 AM if parsing fails
        return time(9, 0), normalized_tz

    @staticmethod
    def create_datetime_with_timezone(
        date_obj: date,
        time_obj: time,
        user_timezone: str = 'UTC'
    ) -> datetime:
        """
        Create a timezone-aware datetime object.

        Args:
            date_obj: Date object
            time_obj: Time object
            user_timezone: User's timezone

        Returns:
            Timezone-aware datetime object
        """
        normalized_tz = TimezoneManager.normalize_timezone(user_timezone)
        tz_obj = TimezoneManager.get_timezone_object(normalized_tz)

        # Create naive datetime
        dt = datetime.combine(date_obj, time_obj)

        # Make it timezone-aware
        return tz_obj.localize(dt)

    @staticmethod
    def convert_to_utc(dt: datetime, from_timezone: str = 'UTC') -> datetime:
        """
        Convert a datetime to UTC.

        Args:
            dt: Datetime to convert
            from_timezone: Source timezone

        Returns:
            UTC datetime
        """
        if dt.tzinfo is None:
            # Assume it's in the source timezone
            normalized_tz = TimezoneManager.normalize_timezone(from_timezone)
            tz_obj = TimezoneManager.get_timezone_object(normalized_tz)
            dt = tz_obj.localize(dt)

        return dt.astimezone(pytz.UTC)

    @staticmethod
    def format_time_for_display(dt: datetime, user_timezone: str = 'UTC') -> str:
        """
        Format datetime for user display in their timezone.

        Args:
            dt: Datetime to format
            user_timezone: User's timezone

        Returns:
            Formatted time string
        """
        normalized_tz = TimezoneManager.normalize_timezone(user_timezone)
        tz_obj = TimezoneManager.get_timezone_object(normalized_tz)

        if dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)

        local_dt = dt.astimezone(tz_obj)
        return local_dt.strftime('%I:%M %p')


# Convenience functions
def parse_user_time(time_input: str, user_timezone: str = 'UTC') -> tuple[time, str]:
    """Parse user time input and return time object with timezone."""
    return TimezoneManager.parse_time_with_timezone(time_input, user_timezone)


def get_user_timezone_object(user_timezone: str) -> pytz.BaseTzInfo:
    """Get timezone object for user."""
    return TimezoneManager.get_timezone_object(
        TimezoneManager.normalize_timezone(user_timezone)
    )


def format_time_for_user(dt: datetime, user_timezone: str = 'UTC') -> str:
    """Format datetime for user display."""
    return TimezoneManager.format_time_for_display(dt, user_timezone)


