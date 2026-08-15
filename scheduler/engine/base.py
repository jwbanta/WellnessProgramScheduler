"""Base class and common helpers for scheduling engines."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
from scheduler.models import (
    Attendee,
    AttendeeSchedule,
    ClassRoster,
    ScheduleResult,
    WellnessClass,
)


class BaseScheduler(ABC):
    """Abstract base class for all scheduler implementations."""

    @abstractmethod
    def schedule(
        self,
        classes: List[WellnessClass],
        attendees: List[Attendee],
        **kwargs,
    ) -> ScheduleResult:
        """
        Takes a list of classes and attendees, produces an optimized ScheduleResult.
        """
        pass

    @staticmethod
    def get_preference_score(rank: int) -> float:
        """
        Calculates a satisfaction score for a preference rank.
        Rank 1 -> 100.0, Rank 2 -> 75.0, Rank 3 -> 50.0, Rank 4 -> 30.0, Rank 5 -> 15.0, etc.
        """
        if rank <= 0:
            return 0.0
        scores = {1: 100.0, 2: 75.0, 3: 50.0, 4: 30.0, 5: 15.0}
        if rank in scores:
            return scores[rank]
        return max(5.0, 10.0 - (rank - 5))

    @staticmethod
    def build_lookup_maps(
        classes: List[WellnessClass],
    ) -> Tuple[Dict[str, WellnessClass], Dict[str, WellnessClass]]:
        """
        Builds lookup maps by ID and by normalized title.
        """
        by_id: Dict[str, WellnessClass] = {c.id: c for c in classes}
        by_title: Dict[str, WellnessClass] = {c.title.strip().lower(): c for c in classes}
        return by_id, by_title

    @staticmethod
    def initialize_result(
        classes: List[WellnessClass],
        attendees: List[Attendee],
    ) -> ScheduleResult:
        """Initializes empty result structures."""
        result = ScheduleResult()
        for c in classes:
            result.class_rosters[c.id] = ClassRoster(wellness_class=c)
        for a in attendees:
            result.attendee_schedules[a.id] = AttendeeSchedule(attendee=a)
        return result
