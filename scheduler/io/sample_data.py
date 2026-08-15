"""Realistic sample dataset generator for wellness programs."""

from __future__ import annotations

import csv
import os
import random
from typing import List, Tuple
from scheduler.models import Attendee, Timeslot, WellnessClass


def get_sample_classes() -> List[WellnessClass]:
    """Returns a curated list of realistic wellness program classes."""
    return [
        WellnessClass(
            id="C101",
            title="Morning Vinyasa Yoga",
            timeslot=Timeslot("09:00 AM", "10:00 AM", label="09:00 AM - 10:00 AM"),
            capacity=12,
            instructor="Elena Vance",
            room="Studio A (Lotus)",
            category="Yoga",
            description="Energizing morning flow for all levels.",
        ),
        WellnessClass(
            id="C102",
            title="Breathwork & Meditation",
            timeslot=Timeslot("09:00 AM", "10:00 AM", label="09:00 AM - 10:00 AM"),
            capacity=10,
            instructor="Marcus Chen",
            room="Studio B (Zen)",
            category="Mindfulness",
            description="Calm the nervous system with somatic breathwork.",
        ),
        WellnessClass(
            id="C103",
            title="Functional HIIT & Core",
            timeslot=Timeslot("09:00 AM", "10:00 AM", label="09:00 AM - 10:00 AM"),
            capacity=8,
            instructor="Jake Miller",
            room="Fitness Studio",
            category="Fitness",
            description="High-energy full body conditioning.",
        ),
        WellnessClass(
            id="C201",
            title="Sound Bath Deep Relaxation",
            timeslot=Timeslot("10:30 AM", "11:30 AM", label="10:30 AM - 11:30 AM"),
            capacity=15,
            instructor="Maya Lin",
            room="Studio B (Zen)",
            category="Sound Therapy",
            description="Tibetan singing bowls and acoustic sound healing.",
        ),
        WellnessClass(
            id="C202",
            title="Pilates Mat Flow",
            timeslot=Timeslot("10:30 AM", "11:30 AM", label="10:30 AM - 11:30 AM"),
            capacity=10,
            instructor="Sarah Jenkins",
            room="Studio A (Lotus)",
            category="Pilates",
            description="Core strengthening and spinal alignment.",
        ),
        WellnessClass(
            id="C203",
            title="Longevity & Nutrition Q&A",
            timeslot=Timeslot("10:30 AM", "11:30 AM", label="10:30 AM - 11:30 AM"),
            capacity=20,
            instructor="Dr. Rachel Green",
            room="Conference Hall",
            category="Nutrition",
            description="Evidence-based nutrition strategies for vibrant energy.",
        ),
        WellnessClass(
            id="C301",
            title="Mindful Nature Walk",
            timeslot=Timeslot("01:00 PM", "02:00 PM", label="01:00 PM - 02:00 PM"),
            capacity=16,
            instructor="Liam O'Connor",
            room="Courtyard Garden",
            category="Outdoor",
            description="Guided sensory nature walk and grounding.",
        ),
        WellnessClass(
            id="C302",
            title="Restorative Yin Yoga",
            timeslot=Timeslot("01:00 PM", "02:00 PM", label="01:00 PM - 02:00 PM"),
            capacity=12,
            instructor="Elena Vance",
            room="Studio A (Lotus)",
            category="Yoga",
            description="Deep tissue release and passive posture holding.",
        ),
        WellnessClass(
            id="C303",
            title="Mobility & Posture Workshop",
            timeslot=Timeslot("01:00 PM", "02:00 PM", label="01:00 PM - 02:00 PM"),
            capacity=10,
            instructor="Jake Miller",
            room="Fitness Studio",
            category="Fitness",
            description="Relieve desk tension with functional mobility drills.",
        ),
        WellnessClass(
            id="C401",
            title="Guided Aromatherapy & Nidra",
            timeslot=Timeslot("02:30 PM", "03:30 PM", label="02:30 PM - 03:30 PM"),
            capacity=14,
            instructor="Maya Lin",
            room="Studio B (Zen)",
            category="Mindfulness",
            description="Yogic sleep meditation with botanical essential oils.",
        ),
        WellnessClass(
            id="C402",
            title="Closing Sound Ceremony",
            timeslot=Timeslot("02:30 PM", "03:30 PM", label="02:30 PM - 03:30 PM"),
            capacity=20,
            instructor="Marcus Chen",
            room="Main Sanctuary",
            category="Sound Therapy",
            description="Communal sound meditation and closing reflections.",
        ),
    ]


def get_sample_attendees(count: int = 35) -> List[Attendee]:
    """Generates realistic sample attendees with ranked preferences across timeslot blocks."""
    names = [
        ("Sophia", "Taylor"),
        ("Liam", "Smith"),
        ("Olivia", "Johnson"),
        ("Noah", "Williams"),
        ("Emma", "Brown"),
        ("Jackson", "Jones"),
        ("Ava", "Garcia"),
        ("Aiden", "Miller"),
        ("Isabella", "Davis"),
        ("Lucas", "Rodriguez"),
        ("Mia", "Martinez"),
        ("Oliver", "Hernandez"),
        ("Harper", "Lopez"),
        ("Ethan", "Gonzalez"),
        ("Evelyn", "Wilson"),
        ("Mason", "Anderson"),
        ("Abigail", "Thomas"),
        ("Logan", "Taylor"),
        ("Emily", "Moore"),
        ("James", "Jackson"),
        ("Ella", "Martin"),
        ("Alexander", "Lee"),
        ("Avery", "Perez"),
        ("Benjamin", "Thompson"),
        ("Scarlett", "White"),
        ("Henry", "Harris"),
        ("Grace", "Sanchez"),
        ("Sebastian", "Clark"),
        ("Chloe", "Ramirez"),
        ("Jack", "Lewis"),
        ("Camila", "Robinson"),
        ("Daniel", "Walker"),
        ("Penelope", "Young"),
        ("Matthew", "Allen"),
        ("Riley", "King"),
    ]

    classes = get_sample_classes()
    timeslot_groups: List[List[WellnessClass]] = []
    seen_slots: List[str] = []

    for c in classes:
        slot_str = str(c.timeslot)
        if slot_str not in seen_slots:
            seen_slots.append(slot_str)
            timeslot_groups.append([cls for cls in classes if str(cls.timeslot) == slot_str])

    attendees: List[Attendee] = []
    random.seed(42)  # Deterministic seed for reproducible testing

    for i in range(min(count, len(names))):
        first, last = names[i]
        att_id = f"ATT_{i+1:03d}"
        email = f"{first.lower()}.{last.lower()}@example.com"

        # Pick 1 preferred class from each timeslot block in random order of interest
        prefs: List[str] = []
        # Sample an interest order
        for group in timeslot_groups:
            chosen = random.choice(group)
            prefs.append(chosen.title)

        # Shuffle preference ranks slightly to simulate natural individual variations
        random.shuffle(prefs)

        attendees.append(
            Attendee(
                id=att_id,
                name=f"{first} {last}",
                email=email,
                preferences=prefs,
                max_classes=3,
            )
        )

    return attendees


def generate_sample_files(output_dir: str) -> Tuple[str, str]:
    """Generates sample classes.csv and sample attendees.csv files."""
    os.makedirs(output_dir, exist_ok=True)
    classes = get_sample_classes()
    attendees = get_sample_attendees()

    classes_path = os.path.join(output_dir, "classes.csv")
    attendees_path = os.path.join(output_dir, "attendees.csv")

    # Write classes.csv
    with open(classes_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["class_id", "title", "start_time", "end_time", "capacity", "instructor", "room", "category"],
        )
        writer.writeheader()
        for c in classes:
            writer.writerow({
                "class_id": c.id,
                "title": c.title,
                "start_time": c.timeslot.start_time,
                "end_time": c.timeslot.end_time,
                "capacity": c.capacity,
                "instructor": c.instructor,
                "room": c.room,
                "category": c.category,
            })

    # Write attendees.csv
    with open(attendees_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "attendee_id",
                "name",
                "email",
                "max_classes",
                "preference_1",
                "preference_2",
                "preference_3",
                "preference_4",
            ],
        )
        writer.writeheader()
        for a in attendees:
            row: dict = {
                "attendee_id": a.id,
                "name": a.name,
                "email": a.email,
                "max_classes": a.max_classes,
            }
            for idx, p in enumerate(a.preferences, start=1):
                row[f"preference_{idx}"] = p
            writer.writerow(row)

    return classes_path, attendees_path
