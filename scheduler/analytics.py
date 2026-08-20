"""Analytics and metrics computation for scheduling outcomes."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List
from scheduler.models import ScheduleResult


@dataclass
class ScheduleMetrics:
    """Detailed analytics metrics for a schedule result."""

    total_attendees: int
    scheduled_attendees: int
    unassigned_attendees: int
    total_assigned_seats: int
    total_capacity: int
    overall_utilization_rate: float
    average_satisfaction_score: float
    satisfaction_score_stddev: float
    rank_breakdown: Dict[str, int] = field(default_factory=dict)
    first_choice_satisfaction_rate: float = 0.0
    full_classes_count: int = 0
    underfilled_classes_count: int = 0
    top_demanded_classes: List[str] = field(default_factory=list)
    three_event_complete_count: int = 0
    fair_assigned_count: int = 0
    two_class_assigned_count: int = 0

    def summary_table(self) -> str:
        """Returns a formatted terminal text summary."""
        lines = [
            "===========================================================",
            "             WELLNESS PROGRAM ANALYTICS SUMMARY            ",
            "===========================================================",
            f" Total Attendees Registered : {self.total_attendees}",
            f" Fully Scheduled (3 Events) : {self.three_event_complete_count} ({(self.three_event_complete_count/self.total_attendees*100) if self.total_attendees else 0:.1f}%)",
            f" • 2 Classes Assigned       : {self.two_class_assigned_count} ({(self.two_class_assigned_count/self.total_attendees*100) if self.total_attendees else 0:.1f}%)",
            f" • 1 Fair Session Assigned  : {self.fair_assigned_count} ({(self.fair_assigned_count/self.total_attendees*100) if self.total_attendees else 0:.1f}%)",
            f" Unassigned Attendees       : {self.unassigned_attendees}",
            f" Total Seats Filled         : {self.total_assigned_seats} / {self.total_capacity} ({self.overall_utilization_rate:.1f}% capacity)",
            f" Average Satisfaction Score : {self.average_satisfaction_score:.2f} / 100.0 (stddev: {self.satisfaction_score_stddev:.2f})",
            f" 1st Choice Allocation Rate : {self.first_choice_satisfaction_rate:.1f}% of all class assignments",
            "-----------------------------------------------------------",
            " Preference Rank Breakdown:",
        ]
        for rank_label, count in self.rank_breakdown.items():
            pct = (count / self.total_assigned_seats * 100) if self.total_assigned_seats > 0 else 0.0
            lines.append(f"   • {rank_label:<12}: {count:>4} seats ({pct:.1f}%)")
        lines.append("-----------------------------------------------------------")
        lines.append(f" Classes/Sessions at Full Cap: {self.full_classes_count}")
        lines.append(f" Underfilled Classes (<50%)  : {self.underfilled_classes_count}")
        if self.top_demanded_classes:
            lines.append(f" High Contention Classes     : {', '.join(self.top_demanded_classes[:3])}")
        lines.append("===========================================================")
        return "\n".join(lines)


def calculate_metrics(result: ScheduleResult) -> ScheduleMetrics:
    """Computes comprehensive analytics for a ScheduleResult."""
    total_attendees = len(result.attendee_schedules)
    scheduled_attendees = sum(1 for s in result.attendee_schedules.values() if s.total_events > 0)
    unassigned_attendees = total_attendees - scheduled_attendees

    three_event_complete = sum(
        1 for s in result.attendee_schedules.values()
        if len(s.regular_classes) >= s.attendee.max_classes and len(s.fair_events) >= s.attendee.max_fairs
    )
    two_class_complete = sum(
        1 for s in result.attendee_schedules.values()
        if len(s.regular_classes) >= s.attendee.max_classes
    )
    fair_complete = sum(
        1 for s in result.attendee_schedules.values()
        if len(s.fair_events) >= s.attendee.max_fairs
    )

    total_assigned_seats = len(result.all_assignments)
    total_capacity = sum(r.wellness_class.capacity for r in result.class_rosters.values())
    utilization_rate = (total_assigned_seats / total_capacity * 100) if total_capacity > 0 else 0.0

    # Satisfaction scores per attendee
    scores: List[float] = []
    for s in result.attendee_schedules.values():
        att_score = sum(asgn.satisfaction_score for asgn in s.assignments)
        scores.append(att_score)

    avg_score = (sum(scores) / len(scores)) if scores else 0.0
    variance = (sum((x - avg_score) ** 2 for x in scores) / len(scores)) if scores else 0.0
    stddev = math.sqrt(variance)

    # Rank breakdown
    rank_counts: Dict[str, int] = {
        "1st Choice": 0,
        "2nd Choice": 0,
        "3rd Choice": 0,
        "4th+ Choice": 0,
        "Fair Session": 0,
        "Open/Unranked": 0,
    }

    first_choice_count = 0
    regular_assigned_count = 0
    for asgn in result.all_assignments:
        w_class = result.class_rosters[asgn.class_id].wellness_class
        if w_class.is_fair:
            rank_counts["Fair Session"] += 1
        elif asgn.preference_rank == 1:
            rank_counts["1st Choice"] += 1
            first_choice_count += 1
            regular_assigned_count += 1
        elif asgn.preference_rank == 2:
            rank_counts["2nd Choice"] += 1
            regular_assigned_count += 1
        elif asgn.preference_rank == 3:
            rank_counts["3rd Choice"] += 1
            regular_assigned_count += 1
        elif asgn.preference_rank >= 4:
            rank_counts["4th+ Choice"] += 1
            regular_assigned_count += 1
        else:
            rank_counts["Open/Unranked"] += 1
            regular_assigned_count += 1

    first_choice_rate = (first_choice_count / regular_assigned_count * 100) if regular_assigned_count > 0 else 0.0

    # Class capacity metrics
    full_count = 0
    underfilled_count = 0
    contended_classes: List[str] = []

    for r in result.class_rosters.values():
        if r.is_full:
            full_count += 1
            if len(r.waitlist) > 0:
                contended_classes.append(f"{r.wellness_class.title} ({len(r.waitlist)} on waitlist)")
        elif r.fill_percentage < 50.0:
            underfilled_count += 1

    return ScheduleMetrics(
        total_attendees=total_attendees,
        scheduled_attendees=scheduled_attendees,
        unassigned_attendees=unassigned_attendees,
        total_assigned_seats=total_assigned_seats,
        total_capacity=total_capacity,
        overall_utilization_rate=round(utilization_rate, 2),
        average_satisfaction_score=round(avg_score, 2),
        satisfaction_score_stddev=round(stddev, 2),
        rank_breakdown=rank_counts,
        first_choice_satisfaction_rate=round(first_choice_rate, 2),
        full_classes_count=full_count,
        underfilled_classes_count=underfilled_count,
        top_demanded_classes=contended_classes,
        three_event_complete_count=three_event_complete,
        fair_assigned_count=fair_complete,
        two_class_assigned_count=two_class_complete,
    )
