"""Unit tests for constraint validation."""

import unittest
from scheduler.engine.validator import ScheduleValidator
from scheduler.models import (
    Attendee,
    AttendeeSchedule,
    ClassRoster,
    ScheduleResult,
    Timeslot,
    WellnessClass,
)


class TestValidator(unittest.TestCase):
    def setUp(self):
        self.c1 = WellnessClass(
            id="C1",
            title="Yoga",
            timeslot=Timeslot("09:00", "10:00"),
            capacity=2,
        )
        self.c2 = WellnessClass(
            id="C2",
            title="Meditation",
            timeslot=Timeslot("09:30", "10:30"),  # Overlaps with C1
            capacity=5,
        )
        self.c3 = WellnessClass(
            id="C3",
            title="Pilates",
            timeslot=Timeslot("11:00", "12:00"),  # Does not overlap
            capacity=5,
        )
        self.a1 = Attendee(id="A1", name="Alice", email="a@example.com", max_classes=2)
        self.a2 = Attendee(id="A2", name="Bob", email="b@example.com", max_classes=2)
        self.a3 = Attendee(id="A3", name="Charlie", email="c@example.com", max_classes=2)

    def test_valid_schedule(self):
        res = ScheduleResult()
        res.class_rosters["C1"] = ClassRoster(wellness_class=self.c1, assigned_attendees=[self.a1, self.a2])
        res.class_rosters["C3"] = ClassRoster(wellness_class=self.c3, assigned_attendees=[self.a1])

        res.attendee_schedules["A1"] = AttendeeSchedule(attendee=self.a1, assigned_classes=[self.c1, self.c3])
        res.attendee_schedules["A2"] = AttendeeSchedule(attendee=self.a2, assigned_classes=[self.c1])

        is_valid, errors = ScheduleValidator.validate(res)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_detects_capacity_overflow(self):
        res = ScheduleResult()
        # C1 capacity is 2, but we put 3 attendees
        res.class_rosters["C1"] = ClassRoster(wellness_class=self.c1, assigned_attendees=[self.a1, self.a2, self.a3])
        res.attendee_schedules["A1"] = AttendeeSchedule(attendee=self.a1, assigned_classes=[self.c1])
        res.attendee_schedules["A2"] = AttendeeSchedule(attendee=self.a2, assigned_classes=[self.c1])
        res.attendee_schedules["A3"] = AttendeeSchedule(attendee=self.a3, assigned_classes=[self.c1])

        is_valid, errors = ScheduleValidator.validate(res)
        self.assertFalse(is_valid)
        self.assertTrue(any("Capacity violation" in e for e in errors))

    def test_detects_attendee_time_overlap(self):
        res = ScheduleResult()
        # A1 assigned to C1 (09:00-10:00) and C2 (09:30-10:30) which overlap
        res.class_rosters["C1"] = ClassRoster(wellness_class=self.c1, assigned_attendees=[self.a1])
        res.class_rosters["C2"] = ClassRoster(wellness_class=self.c2, assigned_attendees=[self.a1])
        res.attendee_schedules["A1"] = AttendeeSchedule(attendee=self.a1, assigned_classes=[self.c1, self.c2])

        is_valid, errors = ScheduleValidator.validate(res)
        self.assertFalse(is_valid)
        self.assertTrue(any("Time conflict" in e for e in errors))

    def test_detects_max_classes_exceeded(self):
        res = ScheduleResult()
        self.a1.max_classes = 1
        res.class_rosters["C1"] = ClassRoster(wellness_class=self.c1, assigned_attendees=[self.a1])
        res.class_rosters["C3"] = ClassRoster(wellness_class=self.c3, assigned_attendees=[self.a1])
        res.attendee_schedules["A1"] = AttendeeSchedule(attendee=self.a1, assigned_classes=[self.c1, self.c3])

        is_valid, errors = ScheduleValidator.validate(res)
        self.assertFalse(is_valid)
        self.assertTrue(any("Max classes exceeded" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
