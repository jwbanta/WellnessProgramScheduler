"""Unit tests for EmailDispatcher."""

import os
import shutil
import tempfile
import unittest
from scheduler.emailer import EmailDispatcher
from scheduler.engine.fair_priority import FairPriorityScheduler
from scheduler.io.exporters import export_email_templates, export_mail_merge_csv
from scheduler.io.sample_data import get_sample_attendees, get_sample_classes


class TestEmailer(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_render_and_preview_dispatch(self):
        classes = get_sample_classes()
        attendees = get_sample_attendees(count=5)
        scheduler = FairPriorityScheduler()
        result = scheduler.schedule(classes, attendees)

        csv_path = os.path.join(self.test_dir, "mail_merge_schedules.csv")
        export_mail_merge_csv(result, csv_path)
        export_email_templates(self.test_dir)

        preview_dir = os.path.join(self.test_dir, "previews")
        dispatcher = EmailDispatcher(from_email="wellness@example.com")

        res = dispatcher.dispatch_from_csv(
            csv_path=csv_path,
            template_dir=self.test_dir,
            dry_run=True,
            preview_output_dir=preview_dir,
        )

        self.assertEqual(res["total_recipients"], 5)
        self.assertEqual(res["sent_count"], 5)
        self.assertEqual(res["failed_count"], 0)
        self.assertGreater(len(res["preview_files"]), 0)

        # Check preview file content
        preview_file = res["preview_files"][0]
        self.assertTrue(os.path.exists(preview_file))
        with open(preview_file, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("Wellness Program Schedule", content)
            self.assertNotIn("{{first_name}}", content)  # Merge tag should be replaced


if __name__ == "__main__":
    unittest.main()
