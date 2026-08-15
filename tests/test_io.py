"""Unit tests for I/O loaders, exporters, and sample data generator."""

import csv
import os
import shutil
import tempfile
import unittest
from scheduler.engine.fair_priority import FairPriorityScheduler
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
    load_classes_from_csv,
)
from scheduler.io.sample_data import generate_sample_files, get_sample_attendees, get_sample_classes


class TestIO(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_sample_data_generation_and_loading(self):
        classes_path, attendees_path = generate_sample_files(self.test_dir)
        self.assertTrue(os.path.exists(classes_path))
        self.assertTrue(os.path.exists(attendees_path))

        loaded_classes = load_classes_from_csv(classes_path)
        loaded_attendees = load_attendees_from_csv(attendees_path)

        self.assertGreater(len(loaded_classes), 0)
        self.assertGreater(len(loaded_attendees), 0)

        # Check sample attendee fields
        first_att = loaded_attendees[0]
        self.assertTrue(first_att.name)
        self.assertTrue(first_att.email)
        self.assertGreater(len(first_att.preferences), 0)

    def test_mail_merge_export_format(self):
        classes = get_sample_classes()
        attendees = get_sample_attendees(count=10)
        scheduler = FairPriorityScheduler()
        result = scheduler.schedule(classes, attendees)

        mail_merge_file = os.path.join(self.test_dir, "mail_merge_schedules.csv")
        export_mail_merge_csv(result, mail_merge_file)
        self.assertTrue(os.path.exists(mail_merge_file))

        # Inspect CSV structure
        with open(mail_merge_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            self.assertIn("email", fieldnames)
            self.assertIn("first_name", fieldnames)
            self.assertIn("last_name", fieldnames)
            self.assertIn("schedule_summary_text", fieldnames)
            self.assertIn("schedule_summary_html", fieldnames)
            self.assertIn("total_classes_assigned", fieldnames)
            self.assertIn("class_1_title", fieldnames)
            self.assertIn("class_1_time", fieldnames)

            rows = list(reader)
            self.assertEqual(len(rows), 10)
            self.assertTrue(rows[0]["email"])
            self.assertTrue(rows[0]["first_name"])

    def test_email_templates_export(self):
        txt_path, html_path = export_email_templates(self.test_dir)
        self.assertTrue(os.path.exists(txt_path))
        self.assertTrue(os.path.exists(html_path))

        with open(txt_path, "r", encoding="utf-8") as f:
            txt = f.read()
            self.assertIn("{{first_name}}", txt)
            self.assertIn("{{schedule_summary_text}}", txt)

        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()
            self.assertIn("{{first_name}}", html)
            self.assertIn("{{schedule_summary_html}}", html)

    def test_other_exporters(self):
        classes = get_sample_classes()
        attendees = get_sample_attendees(count=5)
        scheduler = FairPriorityScheduler()
        result = scheduler.schedule(classes, attendees)

        roster_path = os.path.join(self.test_dir, "rosters.csv")
        master_path = os.path.join(self.test_dir, "master.csv")
        report_path = os.path.join(self.test_dir, "report.md")
        json_path = os.path.join(self.test_dir, "schedule.json")

        export_class_rosters_csv(result, roster_path)
        export_master_schedule_csv(result, master_path)
        export_markdown_report(result, report_path)
        export_json(result, json_path)

        self.assertTrue(os.path.exists(roster_path))
        self.assertTrue(os.path.exists(master_path))
        self.assertTrue(os.path.exists(report_path))
        self.assertTrue(os.path.exists(json_path))


if __name__ == "__main__":
    unittest.main()
