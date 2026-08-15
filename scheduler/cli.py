"""Command-line interface for Wellness Program Scheduler."""

from __future__ import annotations

import argparse
import os
import sys
from typing import List, Optional
from scheduler.analytics import calculate_metrics
from scheduler.engine.fair_priority import FairPriorityScheduler
from scheduler.engine.optimizer import OptimizationScheduler
from scheduler.emailer import EmailDispatcher
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
from scheduler.io.sample_data import generate_sample_files


def _load_data(classes_path: str, attendees_path: str):
    """Auto-detects format (CSV vs JSON) and loads classes & attendees."""
    if classes_path.endswith(".json"):
        classes = load_classes_from_json(classes_path)
    else:
        classes = load_classes_from_csv(classes_path)

    if attendees_path.endswith(".json"):
        attendees = load_attendees_from_json(attendees_path)
    else:
        attendees = load_attendees_from_csv(attendees_path)

    return classes, attendees


def handle_run(args: argparse.Namespace) -> int:
    """Handles the 'run' subcommand to execute scheduling and generate exports."""
    if not os.path.exists(args.classes):
        print(f"Error: Classes file '{args.classes}' not found.", file=sys.stderr)
        return 1
    if not os.path.exists(args.attendees):
        print(f"Error: Attendees file '{args.attendees}' not found.", file=sys.stderr)
        return 1

    print(f"📦 Loading classes from: {args.classes}")
    print(f"👥 Loading attendees from: {args.attendees}")
    classes, attendees = _load_data(args.classes, args.attendees)
    print(f"   Loaded {len(classes)} classes and {len(attendees)} attendees.")

    # Select scheduling engine
    if args.engine == "opt":
        print("⚙️  Running Optimization Solver (ILP / CP-SAT)...")
        scheduler = OptimizationScheduler()
    else:
        print("⚙️  Running Fair Multi-Round Priority Scheduler...")
        scheduler = FairPriorityScheduler(fill_remaining_open_spots=args.fill_open_spots)

    result = scheduler.schedule(classes, attendees)

    if not result.is_valid:
        print("⚠️  Warning: Schedule validation detected issues:", file=sys.stderr)
        for err in result.validation_errors:
            print(f"   - {err}", file=sys.stderr)
    else:
        print("✅ Schedule validated: All hard constraints satisfied (0 overlaps, 0 capacity overflows)!")

    # Output exports
    out_dir = args.output_dir
    os.makedirs(out_dir, exist_ok=True)

    mail_merge_path = os.path.join(out_dir, "mail_merge_schedules.csv")
    rosters_path = os.path.join(out_dir, "class_rosters.csv")
    master_path = os.path.join(out_dir, "master_schedule.csv")
    report_path = os.path.join(out_dir, "schedule_report.md")
    json_path = os.path.join(out_dir, "schedule.json")

    export_mail_merge_csv(result, mail_merge_path)
    export_class_rosters_csv(result, rosters_path)
    export_master_schedule_csv(result, master_path)
    export_markdown_report(result, report_path)
    export_json(result, json_path)
    txt_tmpl, html_tmpl = export_email_templates(out_dir)

    print("\n📁 Exported Deliverables:")
    print(f"   • Mail Merge CSV       : {mail_merge_path}")
    print(f"   • Email Template (Text): {txt_tmpl}")
    print(f"   • Email Template (HTML): {html_tmpl}")
    print(f"   • Class Rosters CSV    : {rosters_path}")
    print(f"   • Master Schedule CSV  : {master_path}")
    print(f"   • Markdown Report      : {report_path}")
    print(f"   • Raw JSON Data        : {json_path}")

    # Compute and display analytics
    metrics = calculate_metrics(result)
    print("\n" + metrics.summary_table() + "\n")
    return 0


def handle_generate_sample(args: argparse.Namespace) -> int:
    """Handles the 'generate-sample' subcommand."""
    out_dir = args.output_dir
    c_path, a_path = generate_sample_files(out_dir)
    print(f"✨ Sample dataset generated successfully in '{out_dir}':")
    print(f"   • Classes CSV   : {c_path}")
    print(f"   • Attendees CSV : {a_path}")
    print("\nRun scheduling on this sample data using:")
    print(f"   wellness-scheduler run --classes {c_path} --attendees {a_path} --output-dir ./results")
    return 0


def handle_send_emails(args: argparse.Namespace) -> int:
    """Handles the 'send-emails' subcommand."""
    if not os.path.exists(args.csv):
        print(f"Error: CSV file '{args.csv}' not found.", file=sys.stderr)
        return 1

    template_dir = args.template_dir or os.path.dirname(args.csv)

    if args.smtp_config and os.path.exists(args.smtp_config):
        dispatcher = EmailDispatcher.from_config_file(args.smtp_config)
    else:
        dispatcher = EmailDispatcher()

    print(f"📧 Processing email dispatch (Mode: {'DRY RUN / PREVIEW' if args.dry_run else 'LIVE SMTP'})...")
    res = dispatcher.dispatch_from_csv(
        csv_path=args.csv,
        template_dir=template_dir,
        dry_run=args.dry_run,
        preview_output_dir=args.preview_dir,
    )

    print(f"   Total Recipients: {res['total_recipients']}")
    print(f"   Processed: {res['sent_count']}")
    if res.get("preview_files"):
        print(f"   Generated {len(res['preview_files'])} preview HTML files in '{args.preview_dir}'.")
    if res.get("errors"):
        print(f"   Errors ({len(res['errors'])}):", file=sys.stderr)
        for err in res["errors"]:
            print(f"     - {err}", file=sys.stderr)
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Builds argument parser for CLI."""
    parser = argparse.ArgumentParser(
        prog="wellness-scheduler",
        description="Wellness Program Scheduler - Fair Constraint Optimization & Mail Merge Exporter",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # Command: run
    p_run = subparsers.add_parser("run", help="Run class scheduling and export schedules")
    p_run.add_argument("--classes", "-c", required=True, help="Path to classes CSV/JSON file")
    p_run.add_argument("--attendees", "-a", required=True, help="Path to attendees CSV/JSON file")
    p_run.add_argument("--output-dir", "-o", default="./results", help="Directory to save exports (default: ./results)")
    p_run.add_argument("--engine", choices=["fair", "opt"], default="fair", help="Scheduling engine (default: fair)")
    p_run.add_argument("--fill-open-spots", action="store_true", help="Fill remaining open spots after preference rounds")

    # Command: generate-sample
    p_sample = subparsers.add_parser("generate-sample", help="Generate realistic sample CSV datasets")
    p_sample.add_argument("--output-dir", "-o", default="./sample_data", help="Output directory (default: ./sample_data)")

    # Command: send-emails
    p_email = subparsers.add_parser("send-emails", help="Preview or dispatch schedule emails via Mail Merge")
    p_email.add_argument("--csv", required=True, help="Path to mail_merge_schedules.csv")
    p_email.add_argument("--template-dir", help="Directory containing email_template.txt/.html (defaults to CSV dir)")
    p_email.add_argument("--smtp-config", help="Path to JSON file with SMTP server credentials")
    p_email.add_argument("--preview-dir", default="./previews", help="Directory to write rendered HTML previews")
    p_email.add_argument("--live", dest="dry_run", action="store_false", help="Actually send emails via live SMTP (default is dry-run)")
    p_email.set_defaults(dry_run=True)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Main CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.subcommand:
        parser.print_help()
        return 0

    if args.subcommand == "run":
        return handle_run(args)
    elif args.subcommand == "generate-sample":
        return handle_generate_sample(args)
    elif args.subcommand == "send-emails":
        return handle_send_emails(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
