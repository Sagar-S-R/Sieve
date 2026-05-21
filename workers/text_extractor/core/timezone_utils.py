"""Timezone conversion utilities for IST to UTC."""
from datetime import datetime, timezone, timedelta
from typing import Optional


# IST timezone (UTC+5:30)
IST_TZ = timezone(timedelta(hours=5, minutes=30))
UTC_TZ = timezone.utc


def convert_ist_to_utc(ist_datetime_str: str) -> Optional[str]:
    """
    Convert IST datetime string to UTC ISO 8601 format.
    
    Args:
        ist_datetime_str: Datetime string in IST (e.g., "2026-05-10T22:00:00")
        
    Returns:
        UTC datetime string in ISO 8601 format (e.g., "2026-05-10T16:30:00Z")
        Returns None if parsing fails
    """
    if not ist_datetime_str:
        return None
    
    try:
        # Remove 'Z' if present (LLM might add it incorrectly)
        ist_datetime_str = ist_datetime_str.replace('Z', '')
        
        # Parse the datetime string
        ist_dt = datetime.fromisoformat(ist_datetime_str)
        
        # If no timezone info, assume IST
        if ist_dt.tzinfo is None:
            ist_dt = ist_dt.replace(tzinfo=IST_TZ)
        
        # Convert to UTC
        utc_dt = ist_dt.astimezone(UTC_TZ)
        
        # Return ISO 8601 format with Z suffix
        return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        
    except Exception as e:
        print(f"Error converting IST to UTC: {e}")
        return None


def get_current_ist_time() -> str:
    """Get current time in IST as formatted string."""
    now_ist = datetime.now(IST_TZ)
    return now_ist.strftime("%Y-%m-%d %H:%M:%S IST")


def get_current_year() -> int:
    """Get current year in IST timezone."""
    return datetime.now(IST_TZ).year


def format_deadline_ist(deadline) -> str:
    """
    Format deadline in user-friendly IST format.
    
    Args:
        deadline: UTC datetime object
        
    Returns:
        Formatted string like "May 12, 2026 at 5:30 PM"
    """
    # Convert to IST
    deadline_ist = deadline.astimezone(IST_TZ)
    
    # Format and remove leading zero from hour
    formatted = deadline_ist.strftime("%B %d, %Y at %I:%M %p")
    return formatted.replace(" 0", " ")
