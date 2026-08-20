"""Pure-Python fair multi-round draft scheduling engine."""

from __future__ import annotations

from typing import Dict, List, Optional, Set
from scheduler.engine.base import BaseScheduler
from scheduler.engine.validator import ScheduleValidator
from scheduler.models import (
    Assignment,
    Attendee,
    AttendeeSchedule,
    ClassRoster,
    ScheduleResult,
    WellnessClass,
)


class FairPriorityScheduler(BaseScheduler):
    """
    Deterministic fair draft scheduling engine.
    Ensures:
    1. Zero time conflicts per attendee.
    2. Zero capacity violations.
    3. Multi-round fairness: Prioritizes attendees with fewer assigned classes in contention rounds.
    """

    def __init__(self, fill_remaining_open_spots: bool = False):
        self.fill_remaining_open_spots = fill_remaining_open_spots

    def _resolve_class(
        self,
        pref: str,
        by_id: Dict[str, WellnessClass],
        by_title: Dict[str, WellnessClass],
    ) -> Optional[WellnessClass]:
        """Resolves a preference string to a WellnessClass by ID or title."""
        pref_clean = pref.strip()
        if pref_clean in by_id:
            return by_id[pref_clean]
        pref_lower = pref_clean.lower()
        if pref_lower in by_title:
            return by_title[pref_lower]
        # Partial match fallback (e.g. "Yoga" matches "Morning Yoga")
        for title_lower, cls_obj in by_title.items():
            if pref_lower in title_lower or title_lower in pref_lower:
                return cls_obj
        return None

    def _can_assign(
        self,
        attendee: Attendee,
        w_class: WellnessClass,
        att_sched: AttendeeSchedule,
        roster: ClassRoster,
    ) -> bool:
        """Checks if attendee can legally be assigned to class/fair without any conflict or overflow."""
        # Check capacity
        if roster.is_full:
            return False

        # Check specific category limits (regular class vs fair session)
        if w_class.is_fair:
            if len(att_sched.fair_events) >= attendee.max_fairs:
                return False
        else:
            if len(att_sched.regular_classes) >= attendee.max_classes:
                return False

        # Check total events limit
        if len(att_sched.assigned_classes) >= attendee.max_total_events:
            return False

        # Check duplicate assignment
        if any(c.id == w_class.id for c in att_sched.assigned_classes):
            return False

        # Check time overlap with existing assigned classes/events
        for existing in att_sched.assigned_classes:
            if existing.timeslot.overlaps(w_class.timeslot):
                return False

        # Check overlap with attendee unavailable timeslots
        for unavail in attendee.unavailable_timeslots:
            if unavail.overlaps(w_class.timeslot):
                return False

        return True

    def _assign(
        self,
        attendee: Attendee,
        w_class: WellnessClass,
        rank: int,
        result: ScheduleResult,
    ) -> None:
        """Executes the assignment and updates rosters and attendee schedules."""
        score = self.get_preference_score(rank) if rank > 0 else (25.0 if w_class.is_fair else 10.0)
        assignment = Assignment(
            attendee_id=attendee.id,
            class_id=w_class.id,
            preference_rank=rank,
            satisfaction_score=score,
        )
        result.all_assignments.append(assignment)

        # Update attendee schedule
        att_sched = result.attendee_schedules[attendee.id]
        att_sched.assignments.append(assignment)
        att_sched.assigned_classes.append(w_class)

        # Update class roster
        roster = result.class_rosters[w_class.id]
        roster.assigned_attendees.append(attendee)

    def schedule(
        self,
        classes: List[WellnessClass],
        attendees: List[Attendee],
        **kwargs,
    ) -> ScheduleResult:
        """Runs the fair draft scheduling algorithm (2 classes + 1 Fair session per individual)."""
        result = self.initialize_result(classes, attendees)
        by_id, by_title = self.build_lookup_maps(classes)

        fair_sessions = [c for c in classes if c.is_fair]
        regular_classes = [c for c in classes if not c.is_fair]

        # Track which preferences have been processed / fulfilled
        processed_preferences: Dict[str, Set[str]] = {a.id: set() for a in attendees}

        # Determine max number of preference rounds
        max_rounds = max((len(a.preferences) for a in attendees), default=0)

        # Phase 1: Preference Draft Rounds
        for round_idx in range(max_rounds):
            rank = round_idx + 1

            # Collect candidates for each class in this round
            class_candidates: Dict[str, List[Attendee]] = {c.id: [] for c in classes}

            for attendee in attendees:
                att_sched = result.attendee_schedules[attendee.id]
                if len(att_sched.assigned_classes) >= attendee.max_total_events:
                    continue

                if round_idx >= len(attendee.preferences):
                    continue

                pref_str = attendee.preferences[round_idx]
                w_class = self._resolve_class(pref_str, by_id, by_title)

                if not w_class:
                    att_sched.unfulfilled_preferences.append(f"{pref_str} (Class not found)")
                    continue

                processed_preferences[attendee.id].add(w_class.id)
                roster = result.class_rosters[w_class.id]

                if self._can_assign(attendee, w_class, att_sched, roster):
                    class_candidates[w_class.id].append(attendee)
                else:
                    # Check reason for unfulfilled
                    if roster.is_full:
                        if attendee not in roster.waitlist:
                            roster.waitlist.append(attendee)
                        att_sched.unfulfilled_preferences.append(f"{w_class.title} (Class at capacity)")
                    elif any(c.timeslot.overlaps(w_class.timeslot) for c in att_sched.assigned_classes):
                        att_sched.unfulfilled_preferences.append(f"{w_class.title} (Time overlap conflict)")
                    elif any(u.overlaps(w_class.timeslot) for u in attendee.unavailable_timeslots):
                        att_sched.unfulfilled_preferences.append(f"{w_class.title} (Unavailable timeslot)")

            # Resolve allocations for each class in this round
            for class_id, candidates in class_candidates.items():
                if not candidates:
                    continue

                w_class = by_id[class_id]
                roster = result.class_rosters[class_id]
                spots = roster.open_spots

                if len(candidates) <= spots:
                    # Everyone in candidate pool gets assigned
                    for attendee in candidates:
                        att_sched = result.attendee_schedules[attendee.id]
                        if self._can_assign(attendee, w_class, att_sched, roster):
                            self._assign(attendee, w_class, rank, result)
                else:
                    # Fair contention sorting:
                    # 1. Attendees with fewest assigned events so far
                    # 2. Attendees with lowest satisfaction score so far
                    # 3. Preservation of stable registration order
                    candidates.sort(
                        key=lambda a: (
                            len(result.attendee_schedules[a.id].assigned_classes),
                            sum(asgn.satisfaction_score for asgn in result.attendee_schedules[a.id].assignments),
                        )
                    )

                    for attendee in candidates:
                        att_sched = result.attendee_schedules[attendee.id]
                        if self._can_assign(attendee, w_class, att_sched, roster):
                            self._assign(attendee, w_class, rank, result)
                        else:
                            if attendee not in roster.waitlist:
                                roster.waitlist.append(attendee)
                            if f"{w_class.title} (Class at capacity)" not in att_sched.unfulfilled_preferences:
                                att_sched.unfulfilled_preferences.append(f"{w_class.title} (Class at capacity)")

        # Phase 2: Fair Session Assignment (Guarantee 1 Fair session per individual)
        if fair_sessions:
            for attendee in attendees:
                att_sched = result.attendee_schedules[attendee.id]
                if len(att_sched.fair_events) >= attendee.max_fairs:
                    continue

                # Find candidate fair sessions that do not conflict with assigned classes
                valid_fairs = [
                    f_sess for f_sess in fair_sessions
                    if self._can_assign(attendee, f_sess, att_sched, result.class_rosters[f_sess.id])
                ]

                if valid_fairs:
                    # Balance load: Pick the Fair session with fewest enrolled attendees
                    valid_fairs.sort(
                        key=lambda f: (
                            result.class_rosters[f.id].enrolled_count,
                            f.timeslot.sort_key(),
                        )
                    )
                    best_fair = valid_fairs[0]
                    self._assign(attendee, best_fair, rank=0, result=result)
                else:
                    # If all non-conflicting fair sessions are full, record in unfulfilled
                    att_sched.unfulfilled_preferences.append("Fair (No available non-conflicting spot)")

        # Phase 3: Fill remaining open regular class spots if requested
        if self.fill_remaining_open_spots:
            for attendee in attendees:
                att_sched = result.attendee_schedules[attendee.id]
                if len(att_sched.regular_classes) < attendee.max_classes:
                    for w_class in regular_classes:
                        roster = result.class_rosters[w_class.id]
                        if self._can_assign(attendee, w_class, att_sched, roster):
                            self._assign(attendee, w_class, rank=0, result=result)
                            if len(att_sched.regular_classes) >= attendee.max_classes:
                                break

        # Compute summary scores
        total_score = sum(asgn.satisfaction_score for asgn in result.all_assignments)
        result.total_satisfaction_score = total_score
        num_attendees = len(attendees)
        result.average_satisfaction_score = round(total_score / num_attendees, 2) if num_attendees > 0 else 0.0

        # Unassigned attendees check
        result.unassigned_attendee_ids = [
            a.id for a in attendees if len(result.attendee_schedules[a.id].assigned_classes) == 0
        ]

        # Validate schedule
        ScheduleValidator.validate(result)
        return result
