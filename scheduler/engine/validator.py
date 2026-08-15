"""Constraint validation engine for Wellness Program Schedules."""

from __future__ import annotations

from typing import List, Tuple
from scheduler.models import ScheduleResult


class ScheduleValidator:
    """Validates that a ScheduleResult strictly respects all hard constraints."""

    @classmethod
    def validate(cls, result: ScheduleResult) -> Tuple[bool, List[str]]:
        """
        Validates the schedule. Returns (is_valid, list_of_error_messages).

        Hard Constraints Enforced:
        1. No Attendee Time Overlaps: An attendee cannot be in 2 classes at the same time.
        2. No Attendee Unavailable Timeslots: An attendee cannot be in a class during unavailable times.
        3. Class Capacity Limit: No class can exceed its maximum capacity.
        4. No Duplicate Enrollments: An attendee cannot be assigned to the same class more than once.
        5. Max Classes Limit: An attendee cannot be assigned more than their max_classes.
        6. Bidirectional Consistency: Class rosters and attendee schedules must agree.
        """
        errors: List[str] = []

        # 1. Validate Class Capacities & Duplicates in Rosters
        for class_id, roster in result.class_rosters.items():
            w_class = roster.wellness_class
            enrolled_ids = [a.id for a in roster.assigned_attendees]

            # Check capacity
            if len(enrolled_ids) > w_class.capacity:
                errors.append(
                    f"Capacity violation: Class '{w_class.title}' (ID: {class_id}) has "
                    f"{len(enrolled_ids)} attendees assigned, exceeding max capacity of {w_class.capacity}."
                )

            # Check for duplicate attendees in the same class
            if len(enrolled_ids) != len(set(enrolled_ids)):
                duplicates = [aid for aid in enrolled_ids if enrolled_ids.count(aid) > 1]
                errors.append(
                    f"Duplicate enrollment: Class '{w_class.title}' (ID: {class_id}) has "
                    f"duplicate attendee assignments for IDs: {set(duplicates)}."
                )

        # 2. Validate Attendee Schedules
        for attendee_id, att_sched in result.attendee_schedules.items():
            attendee = att_sched.attendee
            assigned_classes = att_sched.assigned_classes

            # Check max classes
            if len(assigned_classes) > attendee.max_classes:
                errors.append(
                    f"Max classes exceeded: Attendee '{attendee.name}' (ID: {attendee_id}) is assigned to "
                    f"{len(assigned_classes)} classes (max permitted: {attendee.max_classes})."
                )

            # Check for duplicate class assignments
            assigned_cids = [c.id for c in assigned_classes]
            if len(assigned_cids) != len(set(assigned_cids)):
                errors.append(
                    f"Duplicate class assignment: Attendee '{attendee.name}' (ID: {attendee_id}) is "
                    f"assigned multiple times to the same class: {assigned_cids}."
                )

            # Check for time overlaps among assigned classes
            n = len(assigned_classes)
            for i in range(n):
                for j in range(i + 1, n):
                    c1 = assigned_classes[i]
                    c2 = assigned_classes[j]
                    if c1.timeslot.overlaps(c2.timeslot):
                        errors.append(
                            f"Time conflict: Attendee '{attendee.name}' (ID: {attendee_id}) is assigned to "
                            f"overlapping classes: '{c1.title}' ({c1.timeslot}) and '{c2.title}' ({c2.timeslot})."
                        )

            # Check for conflict with attendee's unavailable timeslots
            for c in assigned_classes:
                for unavail in attendee.unavailable_timeslots:
                    if c.timeslot.overlaps(unavail):
                        errors.append(
                            f"Unavailable time violation: Attendee '{attendee.name}' (ID: {attendee_id}) is "
                            f"assigned to '{c.title}' ({c.timeslot}) which overlaps with unavailable time ({unavail})."
                        )

        # 3. Check Bidirectional Consistency
        for class_id, roster in result.class_rosters.items():
            for att in roster.assigned_attendees:
                att_sched = result.attendee_schedules.get(att.id)
                if not att_sched or not any(c.id == class_id for c in att_sched.assigned_classes):
                    errors.append(
                        f"Consistency error: Attendee '{att.name}' (ID: {att.id}) is on roster for "
                        f"class {class_id}, but the class is missing from their personal schedule."
                    )

        for attendee_id, att_sched in result.attendee_schedules.items():
            for c in att_sched.assigned_classes:
                roster = result.class_rosters.get(c.id)
                if not roster or not any(a.id == attendee_id for a in roster.assigned_attendees):
                    errors.append(
                        f"Consistency error: Class '{c.title}' (ID: {c.id}) is in attendee "
                        f"'{att_sched.attendee.name}' (ID: {attendee_id})'s schedule, but attendee is missing from class roster."
                    )

        is_valid = len(errors) == 0
        result.is_valid = is_valid
        result.validation_errors = errors
        return is_valid, errors
