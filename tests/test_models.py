"""Unit tests for core data models."""

import unittest
from scheduler.models import (
    Attendee,
    AttendeeSchedule,
    ClassRoster,
    Timeslot,
    WellnessClass,
)


class TestModels(unittest.TestCase):
    def test_timeslot_parsing(self):
        ts1 = Timeslot.from_string("09:00 - 10:00")
        self.assertEqual(ts1.start_time, "09:00")
        self.assertEqual(ts1.end_time, "10:00")

        ts2 = Timeslot.from_string("9:30 AM - 10:30 AM", day="Saturday")
        self.assertEqual(ts2.day, "Saturday")
        self.assertEqual(ts2.start_time, "9:30 AM")
        self.assertEqual(ts2.end_time, "10:30 AM")

    def test_timeslot_overlaps(self):
        ts_9_10 = Timeslot("09:00", "10:00")
        ts_930_1030 = Timeslot("09:30", "10:30")
        ts_10_11 = Timeslot("10:00", "11:00")
        ts_11_12 = Timeslot("11:00", "12:00")

        # Overlapping: 09:00-10:00 and 09:30-10:30
        self.assertTrue(ts_9_10.overlaps(ts_930_1030))
        self.assertTrue(ts_930_1030.overlaps(ts_9_10))

        # Adjacent timeslots do not overlap (10:00 is end of one, start of next)
        self.assertFalse(ts_9_10.overlaps(ts_10_11))
        self.assertFalse(ts_10_11.overlaps(ts_11_12))

        # 12-hour AM/PM format overlaps
        ts_am1 = Timeslot("9:00 AM", "10:00 AM")
        ts_am2 = Timeslot("9:30 AM", "10:30 AM")
        ts_pm = Timeslot("1:00 PM", "2:00 PM")
        self.assertTrue(ts_am1.overlaps(ts_am2))
        self.assertFalse(ts_am1.overlaps(ts_pm))

        # Different days do not overlap even if times are identical
        ts_sat = Timeslot("09:00", "10:00", day="Saturday")
        ts_sun = Timeslot("09:00", "10:00", day="Sunday")
        self.assertFalse(ts_sat.overlaps(ts_sun))

    def test_attendee_name_parsing(self):
        a1 = Attendee(id="1", name="Elena Vance", email="elena@example.com")
        self.assertEqual(a1.first_name, "Elena")
        self.assertEqual(a1.last_name, "Vance")

        a2 = Attendee(id="2", name="Cher", email="cher@example.com")
        self.assertEqual(a2.first_name, "Cher")
        self.assertEqual(a2.last_name, "")

    def test_class_roster_capacity(self):
        w_cls = WellnessClass(
            id="C1",
            title="Yoga",
            timeslot=Timeslot("09:00", "10:00"),
            capacity=2,
        )
        roster = ClassRoster(wellness_class=w_cls)
        self.assertEqual(roster.enrolled_count, 0)
        self.assertEqual(roster.open_spots, 2)
        self.assertFalse(roster.is_full)

        a1 = Attendee(id="A1", name="Alice", email="a@example.com")
        a2 = Attendee(id="A2", name="Bob", email="b@example.com")
        roster.assigned_attendees.append(a1)
        self.assertEqual(roster.enrolled_count, 1)
        self.assertEqual(roster.open_spots, 1)
        self.assertEqual(roster.fill_percentage, 50.0)

        roster.assigned_attendees.append(a2)
        self.assertEqual(roster.enrolled_count, 2)
        self.assertEqual(roster.open_spots, 0)
        self.assertTrue(roster.is_full)

    def test_attendee_schedule_summary(self):
        attendee = Attendee(id="A1", name="Alice Smith", email="alice@example.com")
        sched = AttendeeSchedule(attendee=attendee)
        self.assertEqual(sched.summary_text(), "No classes assigned.")

        c1 = WellnessClass(
            id="C1",
            title="Morning Yoga",
            timeslot=Timeslot("09:00 AM", "10:00 AM"),
            capacity=10,
            room="Room A",
            instructor="Elena",
        )
        c2 = WellnessClass(
            id="C2",
            title="Sound Bath",
            timeslot=Timeslot("11:00 AM", "12:00 PM"),
            capacity=10,
            room="Room B",
            instructor="Marcus",
        )
        sched.assigned_classes = [c1, c2]
        text_summary = sched.summary_text()
        self.assertIn("Morning Yoga (Room A) with Elena", text_summary)
        self.assertIn("Sound Bath (Room B) with Marcus", text_summary)

        html_summary = sched.summary_html()
        self.assertTrue(html_summary.startswith("<ul"))
        self.assertIn("Morning Yoga", html_summary)


if __name__ == "__main__":
    unittest.main()
