"""MEMBER 2 - Alerting: log file always; email if SMTP env vars are set."""
import os
import smtplib
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

LOG = Path(__file__).resolve().parent.parent / "data" / "alerts.log"


def send_alerts(source, results, score):
    bad = [r for r in results if r["status"] in ("FAIL", "WARN")]
    if not bad:
        return False
    lines = [f"[{r['status']}] {r['check']} / {r['column']}: {r['detail']}" for r in bad]
    body = f"Data monitor alert for '{source}' (quality score {score}/100)\n\n" + "\n".join(lines)
    LOG.parent.mkdir(exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"\n--- {datetime.now():%Y-%m-%d %H:%M:%S} ---\n{body}\n")
    host, to = os.getenv("SMTP_HOST"), os.getenv("ALERT_TO")
    if host and to:
        try:
            msg = EmailMessage()
            msg["Subject"] = f"Data alert: {source} score {score}/100"
            msg["From"] = os.getenv("SMTP_USER", "monitor@localhost")
            msg["To"] = to
            msg.set_content(body)
            with smtplib.SMTP(host, int(os.getenv("SMTP_PORT", 587))) as s:
                s.starttls()
                if os.getenv("SMTP_USER"):
                    s.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASS", ""))
                s.send_message(msg)
        except Exception as e:
            with open(LOG, "a", encoding="utf-8") as f:
                f.write(f"(email failed: {e})\n")
    return True
