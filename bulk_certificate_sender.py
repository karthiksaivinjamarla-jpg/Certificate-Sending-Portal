#!/usr/bin/env python3
"""Bulk certificate sender.

Reads participant records from CSV and sends personalized emails with
certificate attachments and optional extra information.
"""

from __future__ import annotations

import argparse
import csv
import mimetypes
import smtplib
import ssl
import time
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from typing import Dict, Iterable, List


@dataclass
class SMTPConfig:
    host: str
    port: int
    username: str
    password: str
    sender_name: str
    sender_email: str
    use_tls: bool = True


@dataclass
class SendResult:
    participant_email: str
    status: str
    message: str


def parse_key_value_pairs(values: Iterable[str]) -> Dict[str, str]:
    parsed: Dict[str, str] = {}
    for item in values:
        if "=" not in item:
            raise ValueError(f"Invalid key-value pair '{item}'. Expected key=value.")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"Invalid key-value pair '{item}'. Key cannot be empty.")
        parsed[key] = value
    return parsed


def render_template(template: str, data: Dict[str, str], participant_email: str) -> str:
    try:
        return template.format_map(data)
    except KeyError as error:
        missing_key = error.args[0]
        raise ValueError(
            f"Missing template variable '{missing_key}' for participant '{participant_email}'."
        ) from error


def build_email(
    sender_name: str,
    sender_email: str,
    recipient_email: str,
    subject: str,
    body: str,
    certificate_path: Path,
) -> EmailMessage:
    message = EmailMessage()
    message["From"] = f"{sender_name} <{sender_email}>"
    message["To"] = recipient_email
    message["Subject"] = subject
    message.set_content(body)

    if not certificate_path.exists():
        raise FileNotFoundError(f"Certificate not found at {certificate_path}")

    mime_type, _ = mimetypes.guess_type(certificate_path.name)
    maintype, subtype = (mime_type.split("/", 1) if mime_type else ("application", "octet-stream"))

    with certificate_path.open("rb") as cert_file:
        message.add_attachment(
            cert_file.read(),
            maintype=maintype,
            subtype=subtype,
            filename=certificate_path.name,
        )

    return message


def send_bulk_certificates(
    smtp_config: SMTPConfig,
    participants: List[Dict[str, str]],
    subject_template: str,
    body_template: str,
    certificate_column: str,
    extra_context: Dict[str, str],
    delay_seconds: float,
    dry_run: bool,
) -> List[SendResult]:
    results: List[SendResult] = []

    smtp_client = None
    if not dry_run:
        smtp_client = smtplib.SMTP(smtp_config.host, smtp_config.port, timeout=30)
        if smtp_config.use_tls:
            smtp_client.starttls(context=ssl.create_default_context())
        smtp_client.login(smtp_config.username, smtp_config.password)

    try:
        for participant in participants:
            email = participant.get("email", "").strip()
            if not email:
                results.append(SendResult("", "failed", "Missing email field in CSV row"))
                continue

            context = dict(extra_context)
            context.update(participant)

            try:
                subject = render_template(subject_template, context, email)
                body = render_template(body_template, context, email)
                certificate_value = participant.get(certificate_column, "").strip()
                if not certificate_value:
                    raise ValueError(
                        f"Missing certificate path in column '{certificate_column}'"
                    )
                certificate_path = Path(certificate_value)
                message = build_email(
                    sender_name=smtp_config.sender_name,
                    sender_email=smtp_config.sender_email,
                    recipient_email=email,
                    subject=subject,
                    body=body,
                    certificate_path=certificate_path,
                )
                if dry_run:
                    results.append(SendResult(email, "dry_run", "Prepared successfully"))
                else:
                    assert smtp_client is not None
                    smtp_client.send_message(message)
                    results.append(SendResult(email, "sent", "Delivered successfully"))
            except Exception as exc:  # noqa: BLE001
                results.append(SendResult(email, "failed", str(exc)))

            if delay_seconds > 0:
                time.sleep(delay_seconds)
    finally:
        if smtp_client is not None:
            smtp_client.quit()

    return results


def read_participants(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames is None:
            raise ValueError("CSV file is missing a header row.")
        participants = [row for row in reader]
    if not participants:
        raise ValueError("CSV file has no participant rows.")
    return participants


def write_report(path: Path, results: List[SendResult]) -> None:
    with path.open("w", encoding="utf-8", newline="") as report_file:
        writer = csv.writer(report_file)
        writer.writerow(["email", "status", "message"])
        for result in results:
            writer.writerow([result.participant_email, result.status, result.message])


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Send participation certificates in bulk with personalized extra information."
    )

    parser.add_argument("--participants", required=True, type=Path, help="CSV file path")
    parser.add_argument(
        "--subject",
        required=True,
        help="Subject template, e.g. 'Certificate for {name} - {event_name}'",
    )
    parser.add_argument(
        "--body",
        required=True,
        help="Email body template. Supports placeholders from CSV columns and --extra.",
    )
    parser.add_argument(
        "--certificate-column",
        default="certificate_path",
        help="CSV column containing attachment file path (default: certificate_path)",
    )
    parser.add_argument(
        "--extra",
        action="append",
        default=[],
        help="Extra context key=value. Can be passed multiple times.",
    )
    parser.add_argument("--smtp-host", required=True)
    parser.add_argument("--smtp-port", type=int, default=587)
    parser.add_argument("--smtp-username", required=True)
    parser.add_argument("--smtp-password", required=True)
    parser.add_argument("--sender-name", required=True)
    parser.add_argument("--sender-email", required=True)
    parser.add_argument("--no-tls", action="store_true", help="Disable STARTTLS")
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=0.0,
        help="Optional delay between emails to avoid provider rate limits",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and prepare emails without sending",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("send_report.csv"),
        help="Output CSV report path",
    )
    return parser


def main() -> int:
    parser = create_parser()
    args = parser.parse_args()

    try:
        participants = read_participants(args.participants)
        extra_context = parse_key_value_pairs(args.extra)
        smtp_config = SMTPConfig(
            host=args.smtp_host,
            port=args.smtp_port,
            username=args.smtp_username,
            password=args.smtp_password,
            sender_name=args.sender_name,
            sender_email=args.sender_email,
            use_tls=not args.no_tls,
        )
        results = send_bulk_certificates(
            smtp_config=smtp_config,
            participants=participants,
            subject_template=args.subject,
            body_template=args.body,
            certificate_column=args.certificate_column,
            extra_context=extra_context,
            delay_seconds=args.delay_seconds,
            dry_run=args.dry_run,
        )
        write_report(args.report, results)

        sent = sum(1 for row in results if row.status in {"sent", "dry_run"})
        failed = sum(1 for row in results if row.status == "failed")
        print(f"Completed. Success: {sent}, Failed: {failed}. Report: {args.report}")
        return 0 if failed == 0 else 2
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
