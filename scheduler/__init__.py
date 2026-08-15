"""Wellness Program Scheduler package."""

from scheduler.analytics import calculate_metrics
from scheduler.emailer import EmailDispatcher
from scheduler.engine.fair_priority import FairPriorityScheduler
from scheduler.engine.optimizer import OptimizationScheduler
from scheduler.engine.validator import ScheduleValidator
from scheduler.io.exporters import (
    export_class_rosters_csv,
    export_email_templates,
    export_json,
    export_mail_merge_csv,
    export_markdown_report,
    export_master_schedule_csv,
)
from scheduler.io.loaders import (
    load_attendees_from_csv,
    load_attendees_from_json,
    load_classes_from_csv,
    load_classes_from_json,
)
from scheduler.io.sample_data import generate_sample_files, get_sample_attendees, get_sample_classes
from scheduler.models import (
    Assignment,
    Attendee,
    AttendeeSchedule,
    ClassRoster,
    ScheduleResult,
    Timeslot,
    WellnessClass,
)

__version__ = "0.1.0"
__all__ = [
    "Assignment",
    "Attendee",
    "AttendeeSchedule",
    "ClassRoster",
    "EmailDispatcher",
    "FairPriorityScheduler",
    "OptimizationScheduler",
    "ScheduleResult",
    "ScheduleValidator",
    "Timeslot",
    "WellnessClass",
    "calculate_metrics",
    "export_class_rosters_csv",
    "export_email_templates",
    "export_json",
    "export_mail_merge_csv",
    "export_markdown_report",
    "export_master_schedule_csv",
    "generate_sample_files",
    "get_sample_attendees",
    "get_sample_classes",
    "load_attendees_from_csv",
    "load_attendees_from_json",
    "load_classes_from_csv",
    "load_classes_from_json",
]
