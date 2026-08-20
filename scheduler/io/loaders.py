"""Data loaders for CSV and JSON input formats."""

from __future__ import annotations

import csv
import json
from typing import Any, Dict, List, Optional
from scheduler.models import Attendee, Timeslot, WellnessClass


def _clean_header(name: str) -> str:
    """Normalize header string (lowercased, stripped, underscores for spaces)."""
    return name.strip().lower().replace(" ", "_").replace("-", "_")


def load_classes_from_csv(file_path: str) -> List[WellnessClass]:
    """
    Loads wellness classes from a CSV file.

    Supported headers (case-insensitive):
    - id / class_id
    - title / class_title / name / class_name
    - timeslot / time / time_slot OR start_time + end_time
    - day (optional)
    - capacity / max_capacity / max_attendees / max_size
    - instructor / teacher / coach
    - room / location / studio
    - category / type
    - description / details
    """
    classes: List[WellnessClass] = []
    with open(file_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return classes

        field_map = {_clean_header(k): k for k in reader.fieldnames if k}

        for idx, row in enumerate(reader, start=1):
            def get_val(*aliases: str, default: str = "") -> str:
                for alias in aliases:
                    cleaned = _clean_header(alias)
                    if cleaned in field_map:
                        val = row.get(field_map[cleaned], "").strip()
                        if val:
                            return val
                return default

            class_id = get_val("id", "class_id", default=f"CLASS_{idx:03d}")
            title = get_val("title", "class_title", "name", "class_name", default=f"Class {idx}")

            # Timeslot parsing
            day = get_val("day", "date", default="")
            timeslot_str = get_val("timeslot", "time", "time_slot")
            start_time = get_val("start_time", "start")
            end_time = get_val("end_time", "end")

            if timeslot_str:
                timeslot = Timeslot.from_string(timeslot_str, day=day)
            elif start_time and end_time:
                timeslot = Timeslot(start_time=start_time, end_time=end_time, day=day, label=f"{start_time} - {end_time}")
            elif start_time:
                timeslot = Timeslot.from_string(start_time, day=day)
            else:
                timeslot = Timeslot(start_time="09:00", end_time="10:00", day=day, label="09:00 - 10:00")

            cap_str = get_val("capacity", "max_capacity", "max_attendees", "max_size", default="20")
            try:
                capacity = int(float(cap_str))
            except ValueError:
                capacity = 20

            instructor = get_val("instructor", "teacher", "coach")
            room = get_val("room", "location", "studio")
            category = get_val("category", "type")
            description = get_val("description", "details")
            is_fair_str = get_val("is_fair", "fair")
            is_fair = is_fair_str.lower() in ("true", "1", "yes", "t", "y") if is_fair_str else False

            classes.append(
                WellnessClass(
                    id=class_id,
                    title=title,
                    timeslot=timeslot,
                    capacity=capacity,
                    instructor=instructor,
                    room=room,
                    category=category,
                    description=description,
                    is_fair=is_fair,
                )
            )

    return classes


def load_attendees_from_csv(file_path: str) -> List[Attendee]:
    """
    Loads attendees and their preferences from a CSV file.

    Supported headers (case-insensitive):
    - id / attendee_id / user_id
    - name / attendee_name / full_name (or first_name + last_name)
    - email / email_address
    - max_classes / max_sessions / target_classes (default: 2)
    - max_fairs / max_fair / target_fairs (default: 1)
    - preferences / class_preferences (comma/semicolon/pipe separated list)
    - OR columnar preference ranks: preference_1, preference_2, preference_3... (or pref_1, choice_1, 1st_choice, etc.)
    """
    attendees: List[Attendee] = []
    with open(file_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return attendees

        field_map = {_clean_header(k): k for k in reader.fieldnames if k}

        for idx, row in enumerate(reader, start=1):
            def get_val(*aliases: str, default: str = "") -> str:
                for alias in aliases:
                    cleaned = _clean_header(alias)
                    if cleaned in field_map:
                        val = row.get(field_map[cleaned], "").strip()
                        if val:
                            return val
                return default

            attendee_id = get_val("id", "attendee_id", "user_id", default=f"ATT_{idx:03d}")
            name = get_val("name", "attendee_name", "full_name")
            if not name:
                first = get_val("first_name", "first")
                last = get_val("last_name", "last")
                name = f"{first} {last}".strip() if (first or last) else f"Attendee {idx}"

            email = get_val("email", "email_address", default=f"attendee{idx}@example.com")

            max_cls_str = get_val("max_classes", "max_sessions", "target_classes", default="2")
            try:
                max_classes = int(float(max_cls_str))
            except ValueError:
                max_classes = 2

            max_fair_str = get_val("max_fairs", "max_fair", "target_fairs", default="1")
            try:
                max_fairs = int(float(max_fair_str))
            except ValueError:
                max_fairs = 1

            # Gather preferences
            preferences: List[str] = []

            # 1. Check for dedicated preference columns like preference_1, pref_1, choice_1, 1st_choice
            pref_columns: List[tuple[int, str]] = []
            for clean_key, orig_key in field_map.items():
                if any(p in clean_key for p in ("pref_", "preference_", "choice_")):
                    import re
                    num_match = re.search(r"\d+", clean_key)
                    if num_match:
                        pref_columns.append((int(num_match.group(0)), orig_key))

            if pref_columns:
                pref_columns.sort(key=lambda x: x[0])
                for _, col in pref_columns:
                    val = row.get(col, "").strip()
                    if val and val not in preferences:
                        preferences.append(val)

            # 2. Check for combined preferences column
            if not preferences:
                comb_pref = get_val("preferences", "class_preferences", "choices", "ranked_preferences")
                if comb_pref:
                    delimiters = [";", "|", ","]
                    for d in delimiters:
                        if d in comb_pref:
                            items = [p.strip() for p in comb_pref.split(d) if p.strip()]
                            preferences.extend(items)
                            break
                    if not preferences and comb_pref.strip():
                        preferences.append(comb_pref.strip())

            # Unavailable timeslots
            unavailable_str = get_val("unavailable", "unavailable_timeslots", "blackout_times")
            unavail_slots: List[Timeslot] = []
            if unavailable_str:
                for slot_s in [s.strip() for s in unavailable_str.split(";") if s.strip()]:
                    unavail_slots.append(Timeslot.from_string(slot_s))

            attendees.append(
                Attendee(
                    id=attendee_id,
                    name=name,
                    email=email,
                    preferences=preferences,
                    max_classes=max_classes,
                    max_fairs=max_fairs,
                    unavailable_timeslots=unavail_slots,
                )
            )

    return attendees


def load_classes_from_json(file_path: str) -> List[WellnessClass]:
    """Loads wellness classes from a JSON file."""
    with open(file_path, mode="r", encoding="utf-8") as f:
        data = json.load(f)

    classes: List[WellnessClass] = []
    for item in data:
        ts_data = item.get("timeslot", {})
        if isinstance(ts_data, str):
            timeslot = Timeslot.from_string(ts_data, day=item.get("day", ""))
        else:
            timeslot = Timeslot(
                start_time=ts_data.get("start_time", "09:00"),
                end_time=ts_data.get("end_time", "10:00"),
                day=ts_data.get("day", item.get("day", "")),
                label=ts_data.get("label", ""),
            )
        classes.append(
            WellnessClass(
                id=item["id"],
                title=item["title"],
                timeslot=timeslot,
                capacity=item.get("capacity", 20),
                instructor=item.get("instructor", ""),
                room=item.get("room", ""),
                category=item.get("category", ""),
                description=item.get("description", ""),
                is_fair=item.get("is_fair", False),
            )
        )
    return classes


def load_attendees_from_json(file_path: str) -> List[Attendee]:
    """Loads attendees and preferences from a JSON file."""
    with open(file_path, mode="r", encoding="utf-8") as f:
        data = json.load(f)

    attendees: List[Attendee] = []
    for item in data:
        unavail = [
            Timeslot.from_string(s) if isinstance(s, str) else Timeslot(**s)
            for s in item.get("unavailable_timeslots", [])
        ]
        attendees.append(
            Attendee(
                id=item["id"],
                name=item["name"],
                email=item["email"],
                preferences=item.get("preferences", []),
                max_classes=item.get("max_classes", 2),
                max_fairs=item.get("max_fairs", 1),
                unavailable_timeslots=unavail,
            )
        )
    return attendees
