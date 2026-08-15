# 🌿 Wellness Program Scheduler - Implementation Walkthrough

The **Wellness Program Scheduler** is a complete Python package for automated class scheduling, attendee assignment under strict capacity & non-overlap constraints, and **Mail Merge** export generation.

---

## 🚀 What Was Built

### 1. Core Domain Models & Constraint Validation
- **[`scheduler/models.py`](../scheduler/models.py)**:
  - `Timeslot`: Robust chronological parsing (12-hour AM/PM and 24-hour), discrete period support, and precise overlap calculations.
  - `WellnessClass`: Model for class title, instructor, room, capacity, category, and timeslot.
  - `Attendee`: Model for name, email, ranked preference list, max classes, and blackout times.
  - `AttendeeSchedule` & `ClassRoster`: Dynamic tracking of enrollments, waitlists, fill percentages, and summary formatters.
- **[`scheduler/engine/validator.py`](../scheduler/engine/validator.py)**:
  - Automated constraint verification:
    - ❌ Zero attendee double-booking across overlapping timeslots.
    - ❌ Zero class capacity overflows.
    - ❌ Zero duplicate class assignments per attendee.
    - ❌ Zero attendee max class limit breaches.
    - ❌ Bidirectional consistency between rosters and attendee schedules.

### 2. Fair Scheduling Engine & Exact Optimizer
- **[`scheduler/engine/fair_priority.py`](../scheduler/engine/fair_priority.py)**:
  - Pure Python multi-round fair draft allocation engine (zero external dependencies required).
  - Draft rounds satisfy 1st choices, then 2nd choices, then 3rd choices.
  - In contention scenarios, equity balancing prioritizes attendees with fewer assigned classes to prevent starvation.
  - Automatically manages class waitlists for unfulfilled preferences.
- **[`scheduler/engine/optimizer.py`](../scheduler/engine/optimizer.py)**:
  - Exact mathematical optimization formulation using Integer Linear Programming (ILP) with automatic seamless fallback.

### 3. Mail Merge & Reporting Deliverables
- **[`scheduler/io/exporters.py`](../scheduler/io/exporters.py)**:
  - **`mail_merge_schedules.csv`**: Flattened single-row-per-attendee CSV containing recipient metadata (`email`, `first_name`, `last_name`), multi-line formatted summary (`schedule_summary_text`), pre-styled HTML snippet (`schedule_summary_html`), slot columns (`class_1_title`, `class_1_time`, `class_1_room`, etc.), and unfulfilled preference notifications.
  - **`email_template.txt` & `email_template.html`**: Ready-to-use mail merge templates matching standard merge tags (`{{first_name}}`, `{{schedule_summary_text}}`, `{{schedule_summary_html}}`).
  - **`class_rosters.csv`**: Detailed class rosters with capacity fill percentage, attendee lists, and waitlist tracking.
  - **`master_schedule.csv`**: Granular relational assignment matrix.
  - **`schedule_report.md`**: Master Markdown report.
  - **`schedule.json`**: Machine-readable JSON output.

### 4. CLI, Analytics & Email Dispatch
- **[`scheduler/cli.py`](../scheduler/cli.py)**:
  - Subcommands: `wellness-scheduler run`, `wellness-scheduler generate-sample`, `wellness-scheduler send-emails`.
- **[`scheduler/analytics.py`](../scheduler/analytics.py)**:
  - Detailed analytics metrics: Satisfaction score distribution, 1st/2nd/3rd choice allocation percentages, capacity utilization, bottleneck detection.
- **[`scheduler/emailer.py`](../scheduler/emailer.py)**:
  - SMTP dispatcher supporting live email sending as well as safe local dry-run preview generation (renders `.html` email files per attendee).

---

## 🧪 Verification & Test Results

### 1. Unit & Integration Tests
All **18 automated unit tests** pass with 100% success rate:
```text
$ python3 -m unittest discover tests
..................
----------------------------------------------------------------------
Ran 18 tests in 0.025s

OK
```

### 2. End-to-End Execution on Input Dataset
Generated and scheduled **11 classes** and **35 attendees** directly from [`input_data/`](../input_data):
```text
$ wellness-scheduler run

📁 Input Directory   : ./input_data
📦 Loading classes   : ./input_data/classes.csv
👥 Loading attendees : ./input_data/attendees.csv
   Loaded 11 classes and 35 attendees.
⚙️  Running Fair Multi-Round Priority Scheduler...
✅ Schedule validated: All hard constraints satisfied (0 overlaps, 0 capacity overflows)!

📁 Exported Deliverables:
   • Mail Merge CSV       : ./results/mail_merge_schedules.csv
   • Email Template (Text): ./results/email_template.txt
   • Email Template (HTML): ./results/email_template.html
   • Class Rosters CSV    : ./results/class_rosters.csv
   • Master Schedule CSV  : ./results/master_schedule.csv
   • Markdown Report      : ./results/schedule_report.md
   • Raw JSON Data        : ./results/schedule.json

===========================================================
             WELLNESS PROGRAM ANALYTICS SUMMARY            
===========================================================
 Total Attendees Registered : 35
 Successfully Scheduled     : 35 (100.0%)
 Unassigned Attendees       : 0
 Total Seats Filled         : 105 / 147 (71.4% capacity)
 Average Satisfaction Score : 223.86 / 100.0 (stddev: 4.64)
 1st Choice Allocation Rate : 33.3% of all assignments
-----------------------------------------------------------
 Preference Rank Breakdown:
   • 1st Choice  :   35 seats (33.3%)
   • 2nd Choice  :   35 seats (33.3%)
   • 3rd Choice  :   33 seats (31.4%)
   • 4th+ Choice :    2 seats (1.9%)
-----------------------------------------------------------
 Classes at 100% Capacity   : 2
 Underfilled Classes (<50%) : 1
 High Contention Classes    : Functional HIIT & Core (2 on waitlist)
===========================================================
```

### 3. Email Preview Validation
Rendered and inspected personalized email templates (`preview_ATT_001.html`) verifying:
- Correct replacement of merge tags (`Sophia`, confirmed classes list, times, rooms, instructors).
- Proper chronological sorting of sessions.
- Responsive HTML styling.

---

## 📦 GitHub Sync
All source files, tests, documentation, and sample datasets are synced:
**Repository**: [https://github.com/jwbanta/WellnessProgramScheduler](https://github.com/jwbanta/WellnessProgramScheduler)
