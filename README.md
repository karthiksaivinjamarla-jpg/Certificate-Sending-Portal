# Certificate Sending Portal (Bulk Certificate Sender)

This repository includes a command-line tool to send participation certificates to many participants in one run, while also sending extra custom information (event name, coordinator name, links, etc.).

## Features

- Send certificates in bulk using a participant CSV file.
- Personalize email subject and body using placeholders.
- Include extra custom values via `--extra key=value`.
- Attach certificate files from a CSV column.
- Generate a delivery report CSV (`sent` / `failed` / `dry_run`).
- Supports `--dry-run` mode to validate everything before real sending.

## Prerequisites

- Python 3.9+
- Access to an SMTP account (Gmail, Outlook, custom SMTP, etc.)

## CSV format

Your participant CSV must include an `email` column and a certificate path column (default: `certificate_path`).

Example (`participants.csv`):

```csv
name,email,certificate_path,team
Aditi,aditi@example.com,certificates/aditi.pdf,Team Alpha
Rahul,rahul@example.com,certificates/rahul.pdf,Team Beta
```

## Usage

```bash
python3 bulk_certificate_sender.py \
  --participants participants.csv \
  --subject "Your Participation Certificate - {event_name}" \
  --body "Hello {name},\n\nThanks for joining {event_name}.\nYour team: {team}\nCoordinator: {coordinator}\n\nBest regards" \
  --extra event_name="Hackathon 2026" \
  --extra coordinator="Priya Sharma" \
  --smtp-host smtp.gmail.com \
  --smtp-port 587 \
  --smtp-username your_account@gmail.com \
  --smtp-password "your-app-password" \
  --sender-name "Certificate Desk" \
  --sender-email your_account@gmail.com \
  --delay-seconds 0.25 \
  --report send_report.csv
```

## Dry run (recommended first)

```bash
python3 bulk_certificate_sender.py \
  --participants participants.csv \
  --subject "Your Participation Certificate - {event_name}" \
  --body "Hello {name}, thanks for joining {event_name}." \
  --extra event_name="Hackathon 2026" \
  --smtp-host smtp.gmail.com \
  --smtp-username test \
  --smtp-password test \
  --sender-name "Certificate Desk" \
  --sender-email your_account@gmail.com \
  --dry-run
```

## Placeholders

You can use placeholders from:

1. CSV columns (`{name}`, `{team}`, etc.)
2. `--extra` values (`{event_name}`, `{coordinator}`, etc.)

If a placeholder is missing for any participant row, that row is marked as failed in the report with an error message.

## Output report

By default, a `send_report.csv` file is generated with columns:

- `email`
- `status` (`sent`, `dry_run`, `failed`)
- `message`

## Notes

- If your provider has limits, use `--delay-seconds` to reduce the send rate.
- For Gmail, use an App Password when 2FA is enabled.
- Use `--no-tls` only if your SMTP server does not support STARTTLS.
