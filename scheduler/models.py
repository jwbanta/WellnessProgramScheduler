"""Data models for Wellness Program Scheduler."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Any, Dict, List, Optional, Tuple


def _parse_time_str(val: str) -> Optional[Tuple[int, int]]:
    """Parse time strings like '09:00', '9:00 AM', '14:30', '2:30 PM' into (hour_24, minute)."""
    if not val:
        return None
    val = val.strip()
    # Match patterns like 9:00 AM, 09:30 PM, 14:00
    match = re.match(r"^(\d{1,2}):(\d{2})(?:\s*([APap][Mm]))?$", val)
    if match:
        hr = int(match.group(1))
        mn = int(match.group(2))
        ampm = match.group(3)
        if ampm:
            ampm = ampm.upper()
            if ampm == "PM" and hr < 12:
                hr += 12
            elif ampm == "AM" and hr == 12:
                hr = 0
        return (hr, mn)
    # Check if integer hour e.g. "9 AM"
    match_hr = re.match(r"^(\d{1,2})(?:\s*([APap][Mm]))$", val)
    if match_hr:
        hr = int(match_hr.group(1))
        ampm = match_hr.group(2).upper()
        if ampm == "PM" and hr < 12:
            hr += 12
        elif ampm == "AM" and hr == 12:
            hr = 0
        return (hr, 0)
    return None


@dataclass(frozen=True)
class Timeslot:
    """Represents a scheduled time window (e.g. '09:00 - 10:00' or 'Saturday 10:00 AM - 11:00 AM')."""

    start_time: str
    end_time: str
    day: str = ""
    label: str = ""

    @classmethod
    def from_string(cls, text: str, day: str = "") -> "Timeslot":
        """Parse a timeslot from string like '09:00 - 10:00' or '9:00 AM - 10:00 AM'."""
        text = text.strip()
        if " - " in text or "-" in text:
            parts = text.split(" - ") if " - " in text else text.split("-")
            return cls(start_time=parts[0].strip(), end_time=parts[1].strip(), day=day, label=text)
        return cls(start_time=text, end_time=text, day=day, label=text)

    def _to_minutes(self, time_val: str) -> Optional[int]:
        parsed = _parse_time_str(time_val)
        if parsed:
            return parsed[0] * 60 + parsed[1]
        return None

    def sort_key(self) -> int:
        """Returns integer minutes from midnight for chronological sorting."""
        m = self._to_minutes(self.start_time)
        return m if m is not None else 0

    def __lt__(self, other: "Timeslot") -> bool:
        if self.day and other.day and self.day != other.day:
            return self.day < other.day
        return self.sort_key() < other.sort_key()

    def overlaps(self, other: "Timeslot") -> bool:
        """Check if two timeslots overlap."""
        # If days are specified and different, they do not overlap
        if self.day and other.day and self.day.strip().lower() != other.day.strip().lower():
            return False

        # Attempt time-based overlap calculation
        s1 = self._to_minutes(self.start_time)
        e1 = self._to_minutes(self.end_time)
        s2 = self._to_minutes(other.start_time)
        e2 = self._to_minutes(other.end_time)

        if s1 is not None and e1 is not None and s2 is not None and e2 is not None:
            # Overlaps if start1 < end2 and start2 < end1
            return max(s1, s2) < min(e1, e2)

        # Fallback to string equality if format is discrete label (e.g. "Slot A")
        return (
            self.start_time.strip().lower() == other.start_time.strip().lower()
            or (self.label and other.label and self.label.strip().lower() == other.label.strip().lower())
        )

    def __str__(self) -> str:
        prefix = f"{self.day} " if self.day else ""
        if self.start_time == self.end_time:
            return f"{prefix}{self.start_time}".strip()
        return f"{prefix}{self.start_time} - {self.end_time}".strip()


@dataclass
class WellnessClass:
    """Represents a wellness class offering."""

    id: str
    title: str
    timeslot: Timeslot
    capacity: int
    instructor: str = ""
    room: str = ""
    category: str = ""
    description: str = ""

    def __str__(self) -> str:
        details = [self.title, str(self.timeslot)]
        if self.room:
            details.append(f"Room: {self.room}")
        if self.instructor:
            details.append(f"Instructor: {self.instructor}")
        return " | ".join(details)


@dataclass
class Attendee:
    """Represents an attendee with class preferences."""

    id: str
    name: str
    email: str
    preferences: List[str] = field(default_factory=list)  # Ordered list of preferred class IDs or titles
    max_classes: int = 10  # Maximum number of classes attendee wants/can take
    unavailable_timeslots: List[Timeslot] = field(default_factory=list)

    @property
    def first_name(self) -> str:
        parts = self.name.strip().split()
        return parts[0] if parts else ""

    @property
    def last_name(self) -> str:
        parts = self.name.strip().split()
        return " ".join(parts[1:]) if len(parts) > 1 else ""


@dataclass
class Assignment:
    """Represents the assignment of an attendee to a class."""

    attendee_id: str
    class_id: str
    preference_rank: int  # 1 for 1st choice, 2 for 2nd choice, etc. (0 if not in preferences)
    satisfaction_score: float = 0.0  # Normalized satisfaction weight (e.g. 100 for 1st choice)


@dataclass
class AttendeeSchedule:
    """The schedule and status for an individual attendee."""

    attendee: Attendee
    assignments: List[Assignment] = field(default_factory=list)
    assigned_classes: List[WellnessClass] = field(default_factory=list)
    unfulfilled_preferences: List[str] = field(default_factory=list)

    @property
    def total_classes(self) -> int:
        return len(self.assigned_classes)

    def summary_text(self) -> str:
        """Human-readable multi-line summary of assigned classes."""
        if not self.assigned_classes:
            return "No classes assigned."
        lines = []
        # Sort assigned classes chronologically
        for c in sorted(self.assigned_classes, key=lambda x: (x.timeslot.day, x.timeslot.sort_key())):
            loc = f" ({c.room})" if c.room else ""
            inst = f" with {c.instructor}" if c.instructor else ""
            lines.append(f"• {c.timeslot}: {c.title}{loc}{inst}")
        return "\n".join(lines)

    def summary_html(self) -> str:
        """HTML snippet representation of assigned classes."""
        if not self.assigned_classes:
            return "<p><em>No classes assigned.</em></p>"
        items = []
        for c in sorted(self.assigned_classes, key=lambda x: (x.timeslot.day, x.timeslot.sort_key())):
            loc = f" <span style='color: #666;'>({c.room})</span>" if c.room else ""
            inst = f" <em>w/ {c.instructor}</em>" if c.instructor else ""
            items.append(f"<li><strong>{c.timeslot}</strong> — {c.title}{loc}{inst}</li>")
        return f"<ul style='margin: 0; padding-left: 20px;'>{''.join(items)}</ul>"


@dataclass
class ClassRoster:
    """The roster and enrollment status for a wellness class."""

    wellness_class: WellnessClass
    assigned_attendees: List[Attendee] = field(default_factory=list)
    waitlist: List[Attendee] = field(default_factory=list)

    @property
    def enrolled_count(self) -> int:
        return len(self.assigned_attendees)

    @property
    def open_spots(self) -> int:
        return max(0, self.wellness_class.capacity - self.enrolled_count)

    @property
    def fill_percentage(self) -> float:
        if self.wellness_class.capacity <= 0:
            return 0.0
        return round((self.enrolled_count / self.wellness_class.capacity) * 100, 1)

    @property
    def is_full(self) -> bool:
        return self.enrolled_count >= self.wellness_class.capacity


@dataclass
class ScheduleResult:
    """The comprehensive result of a scheduling run."""

    class_rosters: Dict[str, ClassRoster] = field(default_factory=dict)
    attendee_schedules: Dict[str, AttendeeSchedule] = field(default_factory=dict)
    all_assignments: List[Assignment] = field(default_factory=list)
    total_satisfaction_score: float = 0.0
    average_satisfaction_score: float = 0.0
    unassigned_attendee_ids: List[str] = field(default_factory=list)
    is_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)
