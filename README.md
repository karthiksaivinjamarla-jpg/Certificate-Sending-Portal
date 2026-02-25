# Certificate Sending Portal

This project helps you send participation certificates to many participants at once, with extra personalized information like event name, coordinator, team, links, etc.

It now supports both:
- **CLI mode** (`bulk_certificate_sender.py`)
- **Web application mode** (`app.py` with Flask)

## Features

- Send certificates in bulk using a participant CSV file.
- Personalize email subject and body using placeholders.
- Include extra custom values via key/value pairs.
- Attach certificate files from a CSV column.
- Generate a delivery report CSV (`sent` / `failed` / `dry_run`).
- Supports dry-run mode to validate before real sending.

## Prerequisites

- Python 3.9+
- SMTP account (Gmail, Outlook, custom SMTP)
- Install dependencies:

```bash
pip install -r requirements.txt
```

## CSV format

Your participant CSV must include:
- `email`
- certificate path column (default: `certificate_path`)

Example (`participants.csv`):

```csv
name,email,certificate_path,team
Aditi,aditi@example.com,certificates/aditi.pdf,Team Alpha
Rahul,rahul@example.com,certificates/rahul.pdf,Team Beta
```

## Option 1: Run as CLI

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

## Option 2: Run as Web Application

Start app:

```bash
python3 app.py
```

Then open:

- `http://localhost:5000`

### Workflow in app

1. Enter participants CSV path.
2. Enter subject/body templates.
3. Add extra values (`key=value`) one per line.
4. Enter SMTP + sender details.
5. Check **Dry Run** first.
6. Click **Start Sending**.
7. Review row-by-row result table and generated report path.

## Placeholders

You can use placeholders from:
1. CSV columns (`{name}`, `{team}`, etc.)
2. Extra values (`{event_name}`, `{coordinator}`, etc.)

If a placeholder is missing for any row, that row is marked failed in report.

## Output report

By default, a report CSV is generated with:
- `email`
- `status` (`sent`, `dry_run`, `failed`)
- `message`

## Notes

- Use `delay` to avoid SMTP rate limits.
- For Gmail, use App Password with 2FA enabled.
- Use no-TLS only if your SMTP server requires it.
