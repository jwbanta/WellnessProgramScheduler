"""Unit tests for scheduling engines."""

import unittest
from scheduler.engine.fair_priority import FairPriorityScheduler
from scheduler.engine.optimizer import OptimizationScheduler
from scheduler.models import Attendee, Timeslot, WellnessClass


class TestEngine(unittest.TestCase):
    def test_fair_priority_basic_assignment(self):
        classes = [
            WellnessClass(
                id="C1",
                title="Morning Yoga",
                timeslot=Timeslot("09:00", "10:00"),
                capacity=2,
            ),
            WellnessClass(
                id="C2",
                title="Sound Bath",
                timeslot=Timeslot("10:30", "11:30"),
                capacity=2,
            ),
        ]
        attendees = [
            Attendee(id="A1", name="Alice", email="a@example.com", preferences=["Morning Yoga", "Sound Bath"], max_classes=2),
            Attendee(id="A2", name="Bob", email="b@example.com", preferences=["Sound Bath", "Morning Yoga"], max_classes=2),
        ]

        scheduler = FairPriorityScheduler()
        result = scheduler.schedule(classes, attendees)

        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.all_assignments), 4)

        # Both got Morning Yoga and Sound Bath
        self.assertEqual(len(result.attendee_schedules["A1"].assigned_classes), 2)
        self.assertEqual(len(result.attendee_schedules["A2"].assigned_classes), 2)

    def test_fair_priority_contention_and_capacity_limit(self):
        # Class C1 has capacity 2, but 5 attendees want it as 1st choice
        classes = [
            WellnessClass(id="C1", title="Hot Yoga", timeslot=Timeslot("09:00", "10:00"), capacity=2),
            WellnessClass(id="C2", title="Meditation", timeslot=Timeslot("09:00", "10:00"), capacity=5),
        ]
        attendees = [
            Attendee(id=f"A{i}", name=f"Attendee {i}", email=f"a{i}@example.com", preferences=["Hot Yoga", "Meditation"])
            for i in range(1, 6)
        ]

        scheduler = FairPriorityScheduler()
        result = scheduler.schedule(classes, attendees)

        self.assertTrue(result.is_valid)
        # Hot Yoga roster MUST have exactly 2 attendees
        self.assertEqual(result.class_rosters["C1"].enrolled_count, 2)
        # 3 attendees on waitlist for Hot Yoga
        self.assertEqual(len(result.class_rosters["C1"].waitlist), 3)

        # The other 3 should have received their second choice (Meditation) in round 2!
        self.assertEqual(result.class_rosters["C2"].enrolled_count, 3)

    def test_fair_priority_prevents_time_overlaps(self):
        # Two classes at the exact same time
        classes = [
            WellnessClass(id="C1", title="Yoga", timeslot=Timeslot("09:00", "10:00"), capacity=5),
            WellnessClass(id="C2", title="HIIT", timeslot=Timeslot("09:00", "10:00"), capacity=5),
            WellnessClass(id="C3", title="Nutrition", timeslot=Timeslot("11:00", "12:00"), capacity=5),
        ]
        # Attendee requests Yoga, HIIT, Nutrition
        attendee = Attendee(id="A1", name="Alice", email="a@example.com", preferences=["Yoga", "HIIT", "Nutrition"])

        scheduler = FairPriorityScheduler()
        result = scheduler.schedule(classes, [attendee])

        self.assertTrue(result.is_valid)
        assigned = result.attendee_schedules["A1"].assigned_classes
        # Alice should get Yoga (1st) and Nutrition (3rd), but NOT HIIT because HIIT overlaps with Yoga
        assigned_titles = [c.title for c in assigned]
        self.assertIn("Yoga", assigned_titles)
        self.assertIn("Nutrition", assigned_titles)
        self.assertNotIn("HIIT", assigned_titles)
        self.assertEqual(len(assigned), 2)

    def test_optimizer_fallback(self):
        classes = [
            WellnessClass(id="C1", title="Yoga", timeslot=Timeslot("09:00", "10:00"), capacity=2),
            WellnessClass(id="C2", title="Sound Bath", timeslot=Timeslot("10:30", "11:30"), capacity=2),
        ]
        attendees = [
            Attendee(id="A1", name="Alice", email="a@example.com", preferences=["Yoga", "Sound Bath"]),
        ]
        opt = OptimizationScheduler()
        result = opt.schedule(classes, attendees)
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.all_assignments), 2)


if __name__ == "__main__":
    unittest.main()
