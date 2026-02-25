#!/usr/bin/env python3
"""Flask application wrapper for bulk_certificate_sender.py."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

from flask import Flask, render_template_string, request

from bulk_certificate_sender import (
    SMTPConfig,
    parse_key_value_pairs,
    read_participants,
    send_bulk_certificates,
    write_report,
)

app = Flask(__name__)

PAGE = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>Certificate Sending Portal</title>
    <style>
      body { font-family: Arial, sans-serif; margin: 2rem auto; max-width: 960px; }
      h1 { margin-bottom: 0.2rem; }
      .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
      .full { grid-column: 1 / -1; }
      label { display: block; font-size: 0.9rem; margin-bottom: 0.3rem; font-weight: 600; }
      input, textarea { width: 100%; padding: 0.55rem; box-sizing: border-box; }
      textarea { min-height: 120px; }
      button { margin-top: 1rem; padding: 0.7rem 1rem; }
      .result { margin-top: 1.2rem; padding: 0.8rem; border-radius: 6px; }
      .ok { background: #ecfdf3; border: 1px solid #9be7bf; }
      .err { background: #fff1f2; border: 1px solid #fecdd3; }
      table { margin-top: 0.8rem; width: 100%; border-collapse: collapse; }
      th, td { border: 1px solid #ddd; padding: 0.5rem; text-align: left; }
    </style>
  </head>
  <body>
    <h1>Certificate Sending Portal</h1>
    <p>Send participation certificates in bulk with extra personalized data.</p>

    <form method="post">
      <div class="grid">
        <div class="full">
          <label>Participants CSV path</label>
          <input name="participants" value="{{form.get('participants', 'sample_data/participants.csv')}}" required />
        </div>

        <div>
          <label>Subject template</label>
          <input name="subject" value="{{form.get('subject', 'Certificate - {event_name}')}}" required />
        </div>
        <div>
          <label>Certificate column</label>
          <input name="certificate_column" value="{{form.get('certificate_column', 'certificate_path')}}" required />
        </div>

        <div class="full">
          <label>Body template</label>
          <textarea name="body" required>{{form.get('body', 'Hello {name}, thanks for joining {event_name}.')}}</textarea>
        </div>

        <div class="full">
          <label>Extra key=value (one per line)</label>
          <textarea name="extra_lines">{{form.get('extra_lines', 'event_name=Hackathon 2026\ncoordinator=Certificate Team')}}</textarea>
        </div>

        <div>
          <label>SMTP Host</label>
          <input name="smtp_host" value="{{form.get('smtp_host', 'smtp.gmail.com')}}" required />
        </div>
        <div>
          <label>SMTP Port</label>
          <input type="number" name="smtp_port" value="{{form.get('smtp_port', '587')}}" required />
        </div>

        <div>
          <label>SMTP Username</label>
          <input name="smtp_username" value="{{form.get('smtp_username', '')}}" required />
        </div>
        <div>
          <label>SMTP Password</label>
          <input type="password" name="smtp_password" value="{{form.get('smtp_password', '')}}" required />
        </div>

        <div>
          <label>Sender Name</label>
          <input name="sender_name" value="{{form.get('sender_name', 'Certificate Desk')}}" required />
        </div>
        <div>
          <label>Sender Email</label>
          <input name="sender_email" value="{{form.get('sender_email', '')}}" required />
        </div>

        <div>
          <label>Delay seconds</label>
          <input name="delay_seconds" type="number" step="0.1" value="{{form.get('delay_seconds', '0')}}" />
        </div>
        <div>
          <label>Report path</label>
          <input name="report" value="{{form.get('report', 'send_report.csv')}}" />
        </div>

        <div>
          <label><input type="checkbox" name="dry_run" {% if form.get('dry_run') %}checked{% endif %}> Dry Run</label>
        </div>
        <div>
          <label><input type="checkbox" name="no_tls" {% if form.get('no_tls') %}checked{% endif %}> Disable TLS</label>
        </div>
      </div>
      <button type="submit">Start Sending</button>
    </form>

    {% if error %}
      <div class="result err"><strong>Error:</strong> {{error}}</div>
    {% endif %}

    {% if summary %}
      <div class="result ok">
        <strong>Completed:</strong> success={{summary.success}} failed={{summary.failed}} report={{summary.report}}
      </div>
      <table>
        <thead><tr><th>Email</th><th>Status</th><th>Message</th></tr></thead>
        <tbody>
          {% for row in rows %}
            <tr><td>{{row.participant_email}}</td><td>{{row.status}}</td><td>{{row.message}}</td></tr>
          {% endfor %}
        </tbody>
      </table>
    {% endif %}
  </body>
</html>
"""


def parse_extra_lines(extra_lines: str) -> Dict[str, str]:
    lines = [line.strip() for line in extra_lines.splitlines() if line.strip()]
    return parse_key_value_pairs(lines)


@app.route("/", methods=["GET", "POST"])
def index() -> str:
    error = ""
    summary = None
    rows = []
    form = request.form.to_dict(flat=True) if request.method == "POST" else {}

    if request.method == "POST":
        form["dry_run"] = "dry_run" if request.form.get("dry_run") else ""
        form["no_tls"] = "no_tls" if request.form.get("no_tls") else ""
        try:
            participants = read_participants(Path(request.form["participants"]))
            extra_context = parse_extra_lines(request.form.get("extra_lines", ""))

            smtp_config = SMTPConfig(
                host=request.form["smtp_host"],
                port=int(request.form["smtp_port"]),
                username=request.form["smtp_username"],
                password=request.form["smtp_password"],
                sender_name=request.form["sender_name"],
                sender_email=request.form["sender_email"],
                use_tls=not bool(request.form.get("no_tls")),
            )

            rows = send_bulk_certificates(
                smtp_config=smtp_config,
                participants=participants,
                subject_template=request.form["subject"],
                body_template=request.form["body"],
                certificate_column=request.form["certificate_column"],
                extra_context=extra_context,
                delay_seconds=float(request.form.get("delay_seconds", "0") or "0"),
                dry_run=bool(request.form.get("dry_run")),
            )

            report_path = Path(request.form.get("report", "send_report.csv"))
            write_report(report_path, rows)

            success = sum(1 for row in rows if row.status in {"sent", "dry_run"})
            failed = sum(1 for row in rows if row.status == "failed")
            summary = {"success": success, "failed": failed, "report": str(report_path)}
        except Exception as exc:  # noqa: BLE001
            error = str(exc)

    return render_template_string(PAGE, error=error, summary=summary, rows=rows, form=form)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
