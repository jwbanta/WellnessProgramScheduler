"""Data exporters for Mail Merge CSVs, Master Rosters, Markdown Reports, and Email Templates."""

from __future__ import annotations

import csv
import json
import os
from typing import Any, Dict, List, Tuple
from scheduler.models import AttendeeSchedule, ClassRoster, ScheduleResult, WellnessClass


def export_mail_merge_csv(result: ScheduleResult, file_path: str) -> None:
    """
    Exports a flat CSV optimized specifically for Mail Merge tools (Google Workspace Mail Merge,
    YAMM, GMass, MS Word + Outlook, Mailchimp, etc.).

    Each row represents one attendee with personalized merge fields:
    - email, first_name, last_name, attendee_name, attendee_id
    - schedule_summary_text: Clean multi-line bulleted string
    - schedule_summary_html: Pre-styled HTML snippet for rich templates
    - total_events_assigned: Total scheduled events (e.g. 3)
    - total_classes_assigned: Total regular classes (e.g. 2)
    - class_1_title, class_1_time, class_1_room, class_1_instructor
    - class_2_title, class_2_time, class_2_room, class_2_instructor
    - fair_title, fair_time, fair_room, fair_instructor
    - unfulfilled_preferences
    """
    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)

    # Determine maximum number of regular classes and total events across attendees
    max_regular_classes = 2
    for att_sched in result.attendee_schedules.values():
        if len(att_sched.regular_classes) > max_regular_classes:
            max_regular_classes = len(att_sched.regular_classes)

    # Build fieldnames
    fieldnames = [
        "email",
        "first_name",
        "last_name",
        "attendee_name",
        "attendee_id",
        "schedule_summary_text",
        "schedule_summary_html",
        "total_events_assigned",
        "total_classes_assigned",
    ]

    # Explicit class_1 and class_2 columns
    for i in range(1, max_regular_classes + 1):
        fieldnames.extend([
            f"class_{i}_title",
            f"class_{i}_time",
            f"class_{i}_room",
            f"class_{i}_instructor",
        ])

    # Fair session columns
    fieldnames.extend([
        "fair_title",
        "fair_time",
        "fair_room",
        "fair_instructor",
    ])

    fieldnames.append("unfulfilled_preferences")

    with open(file_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for att_id, att_sched in result.attendee_schedules.items():
            attendee = att_sched.attendee
            # Sort assigned regular classes chronologically
            sorted_classes = sorted(att_sched.regular_classes, key=lambda c: (c.timeslot.day, c.timeslot.sort_key()))
            fair = att_sched.fair_event

            row: Dict[str, Any] = {
                "email": attendee.email,
                "first_name": attendee.first_name,
                "last_name": attendee.last_name,
                "attendee_name": attendee.name,
                "attendee_id": attendee.id,
                "schedule_summary_text": att_sched.summary_text(),
                "schedule_summary_html": att_sched.summary_html(),
                "total_events_assigned": len(att_sched.assigned_classes),
                "total_classes_assigned": len(sorted_classes),
                "unfulfilled_preferences": "; ".join(att_sched.unfulfilled_preferences) if att_sched.unfulfilled_preferences else "None",
            }

            for i in range(1, max_regular_classes + 1):
                if i <= len(sorted_classes):
                    cls_obj = sorted_classes[i - 1]
                    row[f"class_{i}_title"] = cls_obj.title
                    row[f"class_{i}_time"] = str(cls_obj.timeslot)
                    row[f"class_{i}_room"] = cls_obj.room
                    row[f"class_{i}_instructor"] = cls_obj.instructor
                else:
                    row[f"class_{i}_title"] = ""
                    row[f"class_{i}_time"] = ""
                    row[f"class_{i}_room"] = ""
                    row[f"class_{i}_instructor"] = ""

            if fair:
                row["fair_title"] = fair.title
                row["fair_time"] = str(fair.timeslot)
                row["fair_room"] = fair.room
                row["fair_instructor"] = fair.instructor
            else:
                row["fair_title"] = ""
                row["fair_time"] = ""
                row["fair_room"] = ""
                row["fair_instructor"] = ""

            writer.writerow(row)


def export_class_rosters_csv(result: ScheduleResult, file_path: str) -> None:
    """Exports class rosters with attendance count, waitlists, and attendee lists."""
    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)

    fieldnames = [
        "class_id",
        "title",
        "is_fair",
        "category",
        "timeslot",
        "day",
        "room",
        "instructor",
        "capacity",
        "enrolled_count",
        "open_spots",
        "fill_percentage",
        "attendee_names",
        "attendee_emails",
        "waitlist_count",
        "waitlist_names",
    ]

    with open(file_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for class_id, roster in result.class_rosters.items():
            w_class = roster.wellness_class
            writer.writerow({
                "class_id": class_id,
                "title": w_class.title,
                "is_fair": "Yes" if w_class.is_fair else "No",
                "category": w_class.category,
                "timeslot": str(w_class.timeslot),
                "day": w_class.timeslot.day,
                "room": w_class.room,
                "instructor": w_class.instructor,
                "capacity": w_class.capacity,
                "enrolled_count": roster.enrolled_count,
                "open_spots": roster.open_spots,
                "fill_percentage": f"{roster.fill_percentage}%",
                "attendee_names": ", ".join(a.name for a in roster.assigned_attendees),
                "attendee_emails": ", ".join(a.email for a in roster.assigned_attendees),
                "waitlist_count": len(roster.waitlist),
                "waitlist_names": ", ".join(a.name for a in roster.waitlist),
            })


def export_master_schedule_csv(result: ScheduleResult, file_path: str) -> None:
    """Exports every assignment as a granular relational row."""
    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)

    fieldnames = [
        "class_id",
        "class_title",
        "event_type",
        "timeslot",
        "day",
        "room",
        "instructor",
        "attendee_id",
        "attendee_name",
        "attendee_email",
        "preference_rank",
        "satisfaction_score",
    ]

    with open(file_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for asgn in result.all_assignments:
            roster = result.class_rosters[asgn.class_id]
            att_sched = result.attendee_schedules[asgn.attendee_id]
            w_class = roster.wellness_class
            attendee = att_sched.attendee

            writer.writerow({
                "class_id": w_class.id,
                "class_title": w_class.title,
                "event_type": "Fair" if w_class.is_fair else "Class",
                "timeslot": str(w_class.timeslot),
                "day": w_class.timeslot.day,
                "room": w_class.room,
                "instructor": w_class.instructor,
                "attendee_id": attendee.id,
                "attendee_name": attendee.name,
                "attendee_email": attendee.email,
                "preference_rank": asgn.preference_rank,
                "satisfaction_score": asgn.satisfaction_score,
            })


def export_email_templates(output_dir: str) -> Tuple[str, str]:
    """
    Generates ready-to-use plain-text and HTML email templates with Mail Merge tags.
    Returns (plain_text_path, html_path).
    """
    os.makedirs(output_dir, exist_ok=True)

    txt_content = """Subject: Your Personalized Wellness Program Schedule (3 Scheduled Events)

Hi {{first_name}},

Thank you for registering for our upcoming Wellness Program! Based on your submitted preferences, here is your confirmed 3-event schedule (2 classes + 1 Fair session):

----------------------------------------------------
YOUR CONFIRMED SCHEDULE:
----------------------------------------------------
{{schedule_summary_text}}
----------------------------------------------------

Total Scheduled Events: {{total_events_assigned}} (2 Classes + 1 Fair)

Important Reminders:
• Please arrive 5-10 minutes before each session starts.
• Bring a water bottle and comfortable attire.
• During your scheduled Fair timeslot, explore interactive wellness booths, vendor demos, and biometric screenings.
• If your schedule includes yoga or meditation, mats are provided on-site.

If you have any questions or need to make a change, please reply to this email.

We look forward to seeing you there!

Warm regards,
Wellness Program Team
"""

    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Your Wellness Program Schedule</title>
</head>
<body style="margin: 0; padding: 24px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; color: #1e293b;">
  <table width="100%" border="0" cellspacing="0" cellpadding="0" style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
    <tr>
      <td style="background: linear-gradient(135deg, #0d9488, #0284c7); padding: 32px 24px; text-align: center; color: #ffffff;">
        <h1 style="margin: 0; font-size: 24px; font-weight: 700; letter-spacing: -0.5px;">🌿 Wellness Program Schedule</h1>
        <p style="margin: 8px 0 0; font-size: 15px; opacity: 0.9;">Your 3 Scheduled Events: 2 Classes + 1 Wellness Fair</p>
      </td>
    </tr>
    <tr>
      <td style="padding: 32px 28px;">
        <p style="font-size: 16px; margin: 0 0 16px;">Hi <strong>{{first_name}}</strong>,</p>
        <p style="font-size: 15px; line-height: 1.6; margin: 0 0 24px; color: #475569;">
          Thank you for registering! We've built your personalized schedule with 3 confirmed events: <strong>2 classes</strong> and <strong>1 Fair session</strong>.
        </p>

        <div style="background-color: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 20px; margin-bottom: 24px;">
          <h2 style="margin: 0 0 12px; font-size: 16px; font-weight: 600; color: #166534;">Your Confirmed Schedule ({{total_events_assigned}} Events)</h2>
          <div style="font-size: 15px; line-height: 1.7; color: #1e293b;">
            {{schedule_summary_html}}
          </div>
        </div>

        <div style="background-color: #f8fafc; border-radius: 8px; padding: 16px; margin-bottom: 24px; font-size: 14px; line-height: 1.6; color: #64748b;">
          <strong style="color: #334155;">📍 Event Reminders:</strong>
          <ul style="margin: 8px 0 0; padding-left: 20px;">
            <li>Please arrive 5–10 minutes prior to session start times.</li>
            <li>Wear comfortable clothing and bring a refillable water bottle.</li>
            <li>Explore vendor demos and wellness booths during your assigned Fair time.</li>
            <li>Mats, blocks, and equipment will be sanitized and provided for classes.</li>
          </ul>
        </div>

        <p style="font-size: 14px; color: #64748b; margin: 0;">
          Need to make an adjustment or have questions? Simply reply directly to this email.
        </p>
      </td>
    </tr>
    <tr>
      <td style="background-color: #f1f5f9; padding: 16px 24px; text-align: center; font-size: 12px; color: #94a3b8;">
        © 2026 Wellness Program Scheduler • Designed for mindful wellness
      </td>
    </tr>
  </table>
</body>
</html>
"""

    txt_path = os.path.join(output_dir, "email_template.txt")
    html_path = os.path.join(output_dir, "email_template.html")

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(txt_content)

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return txt_path, html_path


def export_markdown_report(result: ScheduleResult, file_path: str) -> str:
    """Generates a human-readable Markdown summary report."""
    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)

    lines = [
        "# Wellness Program Schedule - Master Report",
        "",
        f"**Validation Status**: {'✅ VALID (All hard constraints satisfied)' if result.is_valid else '❌ INVALID'}",
        f"**Total Assigned Seats**: {len(result.all_assignments)}",
        f"**Average Attendee Satisfaction**: {result.average_satisfaction_score} / 100.0",
        f"**Total Attendees**: {len(result.attendee_schedules)}",
        f"**Unassigned Attendees**: {len(result.unassigned_attendee_ids)}",
        "",
        "---",
        "",
        "## Class Enrollment & Utilization",
        "",
        "| Class ID | Title | Timeslot | Room | Instructor | Capacity | Enrolled | Open | Fill % |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for class_id, roster in result.class_rosters.items():
        c = roster.wellness_class
        lines.append(
            f"| `{c.id}` | {c.title} | {c.timeslot} | {c.room or '-'} | {c.instructor or '-'} | "
            f"{c.capacity} | **{roster.enrolled_count}** | {roster.open_spots} | {roster.fill_percentage}% |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## Attendee Schedules Sample",
        "",
    ])

    for idx, (att_id, att_sched) in enumerate(result.attendee_schedules.items()):
        if idx >= 10:
            lines.append(f"\n*(Showing 10 of {len(result.attendee_schedules)} attendees in preview)*")
            break
        a = att_sched.attendee
        classes_str = ", ".join(f"{c.title} ({c.timeslot})" for c in att_sched.assigned_classes) or "*None*"
        lines.append(f"- **{a.name}** (`{a.email}`): {classes_str}")

    content = "\n".join(lines)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    return content


def export_json(result: ScheduleResult, file_path: str) -> None:
    """Exports full result to JSON."""
    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)

    data = {
        "is_valid": result.is_valid,
        "validation_errors": result.validation_errors,
        "total_satisfaction_score": result.total_satisfaction_score,
        "average_satisfaction_score": result.average_satisfaction_score,
        "classes": {
            cid: {
                "title": r.wellness_class.title,
                "timeslot": str(r.wellness_class.timeslot),
                "capacity": r.wellness_class.capacity,
                "enrolled_count": r.enrolled_count,
                "fill_percentage": r.fill_percentage,
                "enrolled_attendee_ids": [a.id for a in r.assigned_attendees],
                "waitlist_attendee_ids": [a.id for a in r.waitlist],
            }
            for cid, r in result.class_rosters.items()
        },
        "attendees": {
            aid: {
                "name": s.attendee.name,
                "email": s.attendee.email,
                "total_classes": s.total_classes,
                "assigned_class_ids": [c.id for c in s.assigned_classes],
                "unfulfilled_preferences": s.unfulfilled_preferences,
            }
            for aid, s in result.attendee_schedules.items()
        },
    }

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
