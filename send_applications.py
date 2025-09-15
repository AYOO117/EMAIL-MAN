#!/usr/bin/env python3
"""
send_applications.py

Usage:
  # Dry run (preview only)
  python send_applications.py --csv /mnt/data/1000.csv --resume "/mnt/data/Ayush Chauhan.pdf" --dry-run

  # Actually send (make sure SMTP credentials set in env or pass via args)
  python send_applications.py --csv /mnt/data/1000.csv --resume "/mnt/data/Ayush Chauhan.pdf" --send

Notes:
- For Gmail, create an App Password (recommended) and use it as SMTP password.
- Be responsible: don't mass-spam; respect privacy and anti-spam laws.
"""

import csv
import os
import time
import argparse
import logging
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path

# ---- Configuration ----
DEFAULT_DELAY_SECONDS = 3      # wait between sends (throttle)
MAX_RETRIES = 3
RETRY_BACKOFF = 5              # seconds, multiply for subsequent retries

# Template texts for different roles
# ---- Configuration ----
TEMPLATES = {
    "frontend": {
        "subject": "{company} — Frontend Engineer Application — Ayush Chauhan",
        "body": """Hi {contact_name},

Hope you’re doing well! I’m Ayush Chauhan, an engineering intern at Agnitech Forge and an NSUT graduate with a strong foundation in full stack development. I have worked extensively with React, Next.js, and modern frontend systems to build user-friendly, performant applications.

I’m actively looking for fresher opportunities and would love to connect to discuss any possibilities at {company}.

Warm regards,
Ayush
"""
    },
    "backend": {
        "subject": "{company} — Backend Engineer Application — Ayush Chauhan",
        "body": """Hi {contact_name},

Hope you’re doing well! I’m Ayush Chauhan, an engineering intern at Agnitech Forge and an NSUT graduate with a strong foundation in full stack development. I’ve gained hands-on experience with Node.js, Express, and MongoDB, working on APIs, integrations, and backend workflows.

I’m actively looking for fresher opportunities and would love to connect to discuss any possibilities at {company}.

Warm regards,
Ayush
"""
    },
    "software": {
        "subject": "{company} — Software Engineer Application — Ayush Chauhan",
        "body": """Hi {contact_name},

Hope you’re doing well! I’m Ayush Chauhan, an engineering intern at Agnitech Forge and an NSUT graduate with a solid background in full stack software development. My experience spans React, Node.js, MongoDB, and even blockchain development through Solidity projects.

I’m actively looking for fresher opportunities and would love to connect to discuss any possibilities at {company}.

Warm regards,
Ayush
"""
    }
}


# ---- Helper functions ----

def read_csv(path):
    rows = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def build_message(from_name, from_email, to_email, subject, body_text, resume_path):
    msg = EmailMessage()
    msg['From'] = formataddr((from_name, from_email))
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.set_content(body_text)

    # attach resume
    resume_path = Path(resume_path)
    if resume_path.exists():
        with open(resume_path, 'rb') as rf:
            data = rf.read()
        maintype = 'application'
        subtype = 'pdf'
        msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=resume_path.name)
    else:
        raise FileNotFoundError(f"Resume not found at {resume_path}")

    return msg


def send_smtp(smtp_host, smtp_port, smtp_user, smtp_pass, message, use_tls=True):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if use_tls:
                server = smtplib.SMTP(smtp_host, smtp_port, timeout=60)
                server.starttls()
            else:
                server = smtplib.SMTP(smtp_host, smtp_port, timeout=60)
            server.login(smtp_user, smtp_pass)
            server.send_message(message)
            server.quit()
            return True
        except Exception as e:
            logging.exception("Send attempt %s failed: %s", attempt, e)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF * attempt)
            else:
                return False


# ---- Main routine ----

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', required=True, help='Path to CSV file with recipients')
    parser.add_argument('--resume', required=True, help='Path to resume PDF')
    parser.add_argument('--from-email', default=os.getenv('FROM_EMAIL'), help='Sender email (or env FROM_EMAIL)')
    parser.add_argument('--from-name', default=os.getenv('FROM_NAME', 'Ayush Chauhan'), help='Sender display name')
    parser.add_argument('--smtp-host', default=os.getenv('SMTP_HOST', 'smtp.gmail.com'), help='SMTP host')
    parser.add_argument('--smtp-port', type=int, default=int(os.getenv('SMTP_PORT', 587)), help='SMTP port')
    parser.add_argument('--smtp-user', default=os.getenv('SMTP_USER'), help='SMTP username (often same as from-email)')
    parser.add_argument('--smtp-pass', default=os.getenv('SMTP_PASS'), help='SMTP password (app password or SMTP pwd)')
    parser.add_argument('--delay', type=float, default=DEFAULT_DELAY_SECONDS, help='Delay between sends (sec)')
    parser.add_argument('--dry-run', action='store_true', help='Only preview messages, do not send')
    parser.add_argument('--send', action='store_true', help='Actually send emails (requires SMTP settings)')
    args = parser.parse_args()

    logging.basicConfig(filename='email_send.log', level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s')
    logging.info("Starting email run. dry_run=%s, send=%s", args.dry_run, args.send)

    # Basic credential checks if sending
    if args.send:
        if not (args.smtp_user and args.smtp_pass and args.from_email):
            logging.error("SMTP credentials or from-email not provided. Set --smtp-user --smtp-pass --from-email or env vars.")
            print("Missing SMTP settings (SMTP_USER, SMTP_PASS, or FROM_EMAIL). Aborting.")
            return

    rows = read_csv(args.csv)
    if not rows:
        print("No rows found in CSV. Aborting.")
        return

    for i, r in enumerate(rows, start=1):
        to_email = (r.get('email') or '').strip()
        company = (r.get('company') or 'Company').strip()
        contact_name = (r.get('contact_name') or '').strip() or 'Hiring Team'
        preferred = (r.get('role_preference') or '').strip().lower()
        subject_override = (r.get('subject') or '').strip()

        if not to_email:
            logging.warning("Row %d missing email, skipping", i)
            continue

        # pick template
        role = 'software'
        if preferred in ('frontend', 'front-end', 'ui'):
            role = 'frontend'
        elif preferred in ('backend', 'back-end'):
            role = 'backend'

        template = TEMPLATES.get(role)
        subject = subject_override if subject_override else template['subject'].format(company=company)
        body = template['body'].format(contact_name=contact_name, company=company)

        try:
            msg = build_message(args.from_name, args.from_email, to_email, subject, body, args.resume)
        except FileNotFoundError as fe:
            logging.error("Resume file error: %s", fe)
            print(fe)
            return

        # Preview / dry-run
        if args.dry_run or not args.send:
            print("----------")
            print(f"To: {to_email}")
            print(f"Subject: {subject}")
            print(body)
            print("Attachment:", args.resume)
            logging.info("Previewed email to %s (%s)", to_email, company)
        else:
            success = send_smtp(args.smtp_host, args.smtp_port, args.smtp_user, args.smtp_pass, msg)
            if success:
                logging.info("Sent to %s", to_email)
            else:
                logging.error("Failed to send to %s after retries", to_email)

            time.sleep(args.delay)

    logging.info("Run complete.")


if __name__ == "__main__":
    main()
