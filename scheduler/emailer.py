"""Email sending and preview engine for wellness schedules."""

from __future__ import annotations

import csv
import json
import logging
import os
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class EmailDispatcher:
    """Dispatches schedule notification emails using Mail Merge CSV data."""

    def __init__(
        self,
        smtp_host: str = "smtp.gmail.com",
        smtp_port: int = 587,
        smtp_user: str = "",
        smtp_password: str = "",
        use_tls: bool = True,
        from_email: str = "",
        subject_template: str = "Your Confirmed Wellness Program Schedule",
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.use_tls = use_tls
        self.from_email = from_email or smtp_user
        self.subject_template = subject_template

    @classmethod
    def from_config_file(cls, config_path: str) -> "EmailDispatcher":
        """Loads SMTP settings from a JSON file."""
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(
            smtp_host=data.get("smtp_host", "smtp.gmail.com"),
            smtp_port=data.get("smtp_port", 587),
            smtp_user=data.get("smtp_user", ""),
            smtp_password=data.get("smtp_password", ""),
            use_tls=data.get("use_tls", True),
            from_email=data.get("from_email", ""),
            subject_template=data.get("subject_template", "Your Confirmed Wellness Program Schedule"),
        )

    def render_email(
        self,
        row: Dict[str, str],
        txt_template: str,
        html_template: str,
    ) -> MIMEMultipart:
        """Renders plain-text and HTML versions of email replacing merge tags."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = self.subject_template
        msg["From"] = self.from_email
        msg["To"] = row.get("email", "")

        rendered_txt = txt_template
        rendered_html = html_template

        # Replace all tags like {{first_name}}, {{schedule_summary_text}}, etc.
        for key, val in row.items():
            tag = "{{" + key + "}}"
            rendered_txt = rendered_txt.replace(tag, str(val))
            rendered_html = rendered_html.replace(tag, str(val))

        part_txt = MIMEText(rendered_txt, "plain", "utf-8")
        part_html = MIMEText(rendered_html, "html", "utf-8")

        msg.attach(part_txt)
        msg.attach(part_html)
        return msg

    def dispatch_from_csv(
        self,
        csv_path: str,
        template_dir: str,
        dry_run: bool = True,
        delay_seconds: float = 0.5,
        preview_output_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Reads mail_merge_schedules.csv, renders email templates, and either previews
        or sends via SMTP.
        """
        txt_path = os.path.join(template_dir, "email_template.txt")
        html_path = os.path.join(template_dir, "email_template.html")

        if not os.path.exists(txt_path) or not os.path.exists(html_path):
            raise FileNotFoundError(f"Email templates not found in directory '{template_dir}'.")

        with open(txt_path, "r", encoding="utf-8") as f:
            txt_template = f.read()
        with open(html_path, "r", encoding="utf-8") as f:
            html_template = f.read()

        rows: List[Dict[str, str]] = []
        with open(csv_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append(r)

        results = {
            "total_recipients": len(rows),
            "sent_count": 0,
            "failed_count": 0,
            "dry_run": dry_run,
            "preview_files": [],
            "errors": [],
        }

        if dry_run:
            if preview_output_dir:
                os.makedirs(preview_output_dir, exist_ok=True)
            for idx, row in enumerate(rows):
                msg = self.render_email(row, txt_template, html_template)
                if preview_output_dir and idx < 5:
                    prev_file = os.path.join(preview_output_dir, f"preview_{row.get('attendee_id', idx)}.html")
                    with open(prev_file, "w", encoding="utf-8") as f:
                        for part in msg.get_payload():
                            if part.get_content_type() == "text/html":
                                f.write(part.get_payload(decode=True).decode("utf-8"))
                    results["preview_files"].append(prev_file)
                results["sent_count"] += 1
            return results

        # Live SMTP sending
        server = None
        try:
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            if self.use_tls:
                server.starttls()
            if self.smtp_user and self.smtp_password:
                server.login(self.smtp_user, self.smtp_password)

            for row in rows:
                to_addr = row.get("email")
                if not to_addr:
                    continue
                try:
                    msg = self.render_email(row, txt_template, html_template)
                    server.sendmail(self.from_email, [to_addr], msg.as_string())
                    results["sent_count"] += 1
                    time.sleep(delay_seconds)
                except Exception as e:
                    results["failed_count"] += 1
                    results["errors"].append(f"Failed to send to {to_addr}: {e}")
        finally:
            if server:
                server.quit()

        return results
