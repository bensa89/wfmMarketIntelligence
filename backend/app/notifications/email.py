import smtplib
import logging
from email.message import EmailMessage
from typing import List

logger = logging.getLogger(__name__)


def send_crawl_report(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    smtp_from: str,
    recipients: List[str],
    crawl_stats: dict,
) -> None:
    msg = EmailMessage()
    msg["Subject"] = f"[WFM Intel] Crawl abgeschlossen – {crawl_stats['date']}"
    msg["From"] = smtp_from
    msg["To"] = ", ".join(recipients)

    lines = [
        f"Crawl-Bericht vom {crawl_stats['date']} {crawl_stats['time']}",
        "",
        f"Quellen gecrawlt:  {crawl_stats['sources_total']:>4}",
        f"Fehler:            {crawl_stats['errors']:>4}",
        f"Dauer:             {crawl_stats['duration']}",
    ]
    if crawl_stats.get("digest_generated"):
        lines += ["", "Weekly Digest wurde automatisch generiert."]

    msg.set_content("\n".join(lines))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.ehlo()
        if smtp_port != 25:
            server.starttls()
        if smtp_user and smtp_password:
            server.login(smtp_user, smtp_password)
        server.send_message(msg)
