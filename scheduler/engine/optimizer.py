"""Optimization scheduling engine using Integer Linear Programming (ILP) with automatic fallback."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple
from scheduler.engine.base import BaseScheduler
from scheduler.engine.fair_priority import FairPriorityScheduler
from scheduler.engine.validator import ScheduleValidator
from scheduler.models import (
    Assignment,
    Attendee,
    AttendeeSchedule,
    ClassRoster,
    ScheduleResult,
    WellnessClass,
)

logger = logging.getLogger(__name__)


class OptimizationScheduler(BaseScheduler):
    """
    Mathematical optimizer that solves class assignment using Integer Linear Programming (ILP).
    If an external solver library (like PuLP) is not installed, it automatically falls back to
    FairPriorityScheduler.
    """

    def __init__(self, solver_name: str = "pulp"):
        self.solver_name = solver_name
        self.fallback = FairPriorityScheduler()

    def _resolve_preference_rank(
        self,
        attendee: Attendee,
        w_class: WellnessClass,
    ) -> int:
        """Returns 1-based preference rank if attendee requested this class, otherwise 0."""
        target_id = w_class.id.strip().lower()
        target_title = w_class.title.strip().lower()
        for idx, pref in enumerate(attendee.preferences):
            p = pref.strip().lower()
            if p == target_id or p == target_title or p in target_title or target_title in p:
                return idx + 1
        return 0

    def _schedule_with_pulp(
        self,
        classes: List[WellnessClass],
        attendees: List[Attendee],
    ) -> Optional[ScheduleResult]:
        """Solves assignment with PuLP ILP solver."""
        try:
            import pulp
        except ImportError:
            logger.info("PuLP not installed. Falling back to FairPriorityScheduler.")
            return None

        # Build problem
        prob = pulp.LpProblem("WellnessProgramScheduler", pulp.LpMaximize)

        # Decision variables: x[a.id, c.id] = 1 if attendee a is assigned to class c
        x = {}
        for a in attendees:
            for c in classes:
                # Check if attendee has unavailable time overlapping with class
                if any(u.overlaps(c.timeslot) for u in a.unavailable_timeslots):
                    continue
                x[(a.id, c.id)] = pulp.LpVariable(f"x_{a.id}_{c.id}", cat=pulp.LpBinary)

        # Objective Function: Maximize sum of preference scores
        objective_terms = []
        for a in attendees:
            for c in classes:
                if (a.id, c.id) in x:
                    rank = self._resolve_preference_rank(a, c)
                    score = self.get_preference_score(rank) if rank > 0 else 1.0
                    objective_terms.append(score * x[(a.id, c.id)])

        prob += pulp.lpSum(objective_terms)

        # Constraint 1: Class Capacities
        for c in classes:
            class_vars = [x[(a.id, c.id)] for a in attendees if (a.id, c.id) in x]
            if class_vars:
                prob += pulp.lpSum(class_vars) <= c.capacity, f"Cap_{c.id}"

        # Constraint 2: Attendee Max Classes
        for a in attendees:
            att_vars = [x[(a.id, c.id)] for c in classes if (a.id, c.id) in x]
            if att_vars:
                prob += pulp.lpSum(att_vars) <= a.max_classes, f"MaxClass_{a.id}"

        # Constraint 3: No Overlapping Classes per Attendee
        for a in attendees:
            num_classes = len(classes)
            for i in range(num_classes):
                c1 = classes[i]
                if (a.id, c1.id) not in x:
                    continue
                for j in range(i + 1, num_classes):
                    c2 = classes[j]
                    if (a.id, c2.id) not in x:
                        continue
                    if c1.timeslot.overlaps(c2.timeslot):
                        prob += x[(a.id, c1.id)] + x[(a.id, c2.id)] <= 1, f"Overlap_{a.id}_{c1.id}_{c2.id}"

        # Solve silently
        solver = pulp.PULP_CBC_CMD(msg=False)
        status = prob.solve(solver)

        if status != pulp.LpStatusOptimal:
            logger.warning(f"PuLP solver status was not optimal: {pulp.LpStatus[status]}")
            return None

        # Build ScheduleResult from solution
        result = self.initialize_result(classes, attendees)
        by_id, _ = self.build_lookup_maps(classes)
        att_map = {a.id: a for a in attendees}

        for (a_id, c_id), var in x.items():
            if var.varValue is not None and round(var.varValue) == 1:
                attendee = att_map[a_id]
                w_class = by_id[c_id]
                rank = self._resolve_preference_rank(attendee, w_class)
                score = self.get_preference_score(rank) if rank > 0 else 0.0

                asgn = Assignment(
                    attendee_id=a_id,
                    class_id=c_id,
                    preference_rank=rank,
                    satisfaction_score=score,
                )
                result.all_assignments.append(asgn)
                result.attendee_schedules[a_id].assignments.append(asgn)
                result.attendee_schedules[a_id].assigned_classes.append(w_class)
                result.class_rosters[c_id].assigned_attendees.append(attendee)

        # Track unfulfilled preferences & waitlists
        for a in attendees:
            att_sched = result.attendee_schedules[a.id]
            assigned_cids = {c.id for c in att_sched.assigned_classes}
            for pref in a.preferences:
                matched_cls = None
                for c in classes:
                    if pref.strip().lower() in (c.id.lower(), c.title.lower()):
                        matched_cls = c
                        break
                if matched_cls and matched_cls.id not in assigned_cids:
                    roster = result.class_rosters[matched_cls.id]
                    if roster.is_full:
                        if a not in roster.waitlist:
                            roster.waitlist.append(a)
                        att_sched.unfulfilled_preferences.append(f"{matched_cls.title} (Class at capacity)")
                    else:
                        att_sched.unfulfilled_preferences.append(f"{matched_cls.title} (Time overlap conflict)")

        total_score = sum(asgn.satisfaction_score for asgn in result.all_assignments)
        result.total_satisfaction_score = total_score
        num_att = len(attendees)
        result.average_satisfaction_score = round(total_score / num_att, 2) if num_att > 0 else 0.0
        result.unassigned_attendee_ids = [
            a.id for a in attendees if len(result.attendee_schedules[a.id].assigned_classes) == 0
        ]

        ScheduleValidator.validate(result)
        return result

    def schedule(
        self,
        classes: List[WellnessClass],
        attendees: List[Attendee],
        **kwargs,
    ) -> ScheduleResult:
        """Runs the optimization solver with automatic fallback."""
        opt_res = self._schedule_with_pulp(classes, attendees)
        if opt_res is not None and opt_res.is_valid:
            return opt_res
        # Fallback
        return self.fallback.schedule(classes, attendees, **kwargs)
