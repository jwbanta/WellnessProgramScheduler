# 🌿 Wellness Program Scheduler

A Python constraint-satisfaction scheduling and attendee assignment engine with built-in **Mail Merge** exports and customizable email dispatching.

Designed for wellness programs, corporate retreats, conferences, and fitness workshops to automatically build optimal, conflict-free schedules based on attendee preferences and class capacities.

---

## ✨ Features

- **🛡️ Hard Constraint Guarantees**:
  - **Zero Time Overlaps**: Strict validation prevents attendees from being double-booked in overlapping timeslot blocks.
  - **Zero Capacity Violations**: Never over-enrolls classes past maximum seating limits.
  - **Duplicate Prevention**: Guarantees no attendee is registered multiple times for the same session.
- **⚖️ Fair Multi-Round Draft Allocation**:
  - Multi-round priority allocation ensures equitable satisfaction across all participants and prevents attendee starvation.
  - Built-in waitlist tracking for high-contention classes.
  - Optional exact optimization engine via Integer Linear Programming (ILP / CP-SAT).
- **✉️ Mail Merge Ready Out-of-the-Box**:
  - Automatically produces a flattened `mail_merge_schedules.csv` with personalized fields (`email`, `first_name`, `schedule_summary_text`, `schedule_summary_html`, `class_1_title`, `class_1_time`, etc.).
  - Ready for Google Sheets / Gmail Mail Merge, YAMM, GMass, Microsoft Word / Outlook, and Mailchimp.
  - Generates ready-to-use plain-text (`email_template.txt`) and styled HTML (`email_template.html`) templates.
- **📊 Master Reporting & Analytics**:
  - Class rosters with capacity fill percentage and waitlists.
  - Master schedule matrix.
  - Comprehensive satisfaction metrics and terminal analytics dashboard.
- **⚡ Zero External Dependencies Required**:
  - Pure Python standard library core — runs anywhere out of the box with zero installation friction.

---

## 🚀 Quick Start (CLI)

### 1. Installation

Clone the repository and install in editable mode:
```bash
git clone https://github.com/jwbanta/WellnessProgramScheduler.git
cd WellnessProgramScheduler
pip install -e .
```

---

### 2. Prepare Your Input Data (`input_data/`)

Place your classes and attendees files in the [`input_data/`](file:///Users/mcbam/BamStudios/WellnessProgramScheduler/input_data) folder:
- `input_data/classes.csv`
- `input_data/attendees.csv`

Or generate realistic sample data with 1 command:
```bash
wellness-scheduler generate-sample
```

This populates `input_data/classes.csv` and `input_data/attendees.csv`.

---

### 3. Run the Scheduler

Simply execute `wellness-scheduler run`:
```bash
wellness-scheduler run
```

*(Optional flags: `--input-dir ./my_folder`, `--output-dir ./my_results`, `--engine opt`, `--fill-open-spots`)*

You will see instant validation and an analytics report:
```text
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
```

---

## 📧 How to Send Schedules via Mail Merge

### Option 1: Gmail / Google Workspace (Easiest)
1. Open [Google Sheets](https://sheets.new) and import `./results/mail_merge_schedules.csv`.
2. In Gmail, click **Compose** and click the **Mail Merge** icon (or use an add-on like **YAMM** / **GMass**).
3. Copy the contents of `./results/email_template.html` or `./results/email_template.txt`.
4. Use merge tags:
   - `{{first_name}}`
   - `{{schedule_summary_text}}` (or `{{schedule_summary_html}}`)
5. Click **Send**!

### Option 2: Microsoft Word + Outlook
1. Open MS Word and open `email_template.txt` or paste the template.
2. Navigate to **Mailings** > **Select Recipients** > **Use an Existing List...** and choose `mail_merge_schedules.csv`.
3. Insert Merge Fields: `«first_name»`, `«schedule_summary_text»`.
4. Click **Finish & Merge** > **Send Email Messages**.

### Option 3: Built-in Python Preview & SMTP Sender
You can preview rendered HTML emails locally with:
```bash
wellness-scheduler send-emails \
  --csv ./results/mail_merge_schedules.csv \
  --template-dir ./results \
  --preview-dir ./previews
```
This writes individual `.html` files in `./previews/` so you can verify email styling before sending.

---

## 📋 Input File Formats

### `classes.csv`
| Header | Required | Example | Notes |
| :--- | :---: | :--- | :--- |
| `class_id` | Yes | `C101` | Unique class identifier |
| `title` | Yes | `Morning Vinyasa Yoga` | Name of class |
| `start_time` | Yes | `09:00 AM` | Start time (e.g. `09:00` or `9:00 AM`) |
| `end_time` | Yes | `10:00 AM` | End time |
| `capacity` | Yes | `15` | Maximum number of seats |
| `instructor` | No | `Elena Vance` | Instructor / facilitator name |
| `room` | No | `Studio A (Lotus)` | Location or room name |
| `category` | No | `Yoga` | Classification category |

### `attendees.csv`
| Header | Required | Example | Notes |
| :--- | :---: | :--- | :--- |
| `attendee_id` | Yes | `ATT_001` | Unique attendee identifier |
| `name` | Yes | `Sophia Taylor` | Full name (auto-splits first/last) |
| `email` | Yes | `sophia@example.com` | Email address |
| `preference_1` | Yes | `Morning Vinyasa Yoga` | 1st choice class ID or Title |
| `preference_2` | Yes | `Sound Bath Relaxation` | 2nd choice class ID or Title |
| `preference_3` | No | `Pilates Mat Flow` | 3rd choice class ID or Title |
| `max_classes` | No | `3` | Max sessions attendee can receive (default: 10) |

*(Note: Comma or semicolon-separated `preferences` column is also automatically supported).*

---

## 🧪 Running Tests

Run the full automated test suite:
```bash
python3 -m unittest discover tests
```

---

## 📂 Project Structure

```
WellnessProgramScheduler/
├── scheduler/
│   ├── __init__.py           # Main package exports
│   ├── __main__.py           # Python -m scheduler entrypoint
│   ├── models.py             # Dataclasses (Timeslot, WellnessClass, Attendee, Schedules)
│   ├── analytics.py          # Satisfaction, fill rate, & fairness analytics
│   ├── emailer.py            # SMTP dispatcher & HTML email previewer
│   ├── cli.py                # Command-line interface
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── base.py           # Base scheduler definition & scoring
│   │   ├── fair_priority.py  # Deterministic multi-round fair draft engine
│   │   ├── optimizer.py      # ILP / CP-SAT exact solver with fallback
│   │   └── validator.py      # Hard constraint verification engine
│   └── io/
│       ├── __init__.py
│       ├── loaders.py        # CSV/JSON ingestion with flexible aliases
│       ├── exporters.py      # Mail Merge CSV, Rosters, & Email template exporter
│       └── sample_data.py    # Realistic wellness mock data generator
├── tests/
│   ├── test_models.py        # Timeslot parsing & overlap test suite
│   ├── test_validator.py     # Constraint violation detection tests
│   ├── test_engine.py        # Engine fairness & contention tests
│   ├── test_io.py            # CSV/JSON import/export tests
│   └── test_emailer.py       # Template rendering & preview tests
├── pyproject.toml            # Package build configuration
├── requirements.txt          # Python requirements
└── README.md
```

---

## 📄 License

MIT License. Designed with care for wellness communities.
