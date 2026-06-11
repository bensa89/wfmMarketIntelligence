import pytest
from datetime import date
from unittest.mock import patch, MagicMock
from app.notifications.email import send_crawl_report, send_digest_email
from app.models.digest import WeeklyDigest


def make_test_digest() -> WeeklyDigest:
    return WeeklyDigest(
        id="test-digest-abc",
        week_start=date(2026, 6, 9),
        week_end=date(2026, 6, 15),
        summary="KI dominiert den WFM-Markt diese Woche.",
        sections=[
            {
                "key": "competitors",
                "title": "Wettbewerber",
                "items": [
                    {
                        "signal_id": "sig-1",
                        "company": "Workday",
                        "title": "Workday startet KI-Planungsassistent",
                        "narrative": "Workday präsentierte ein neues KI-Tool.",
                        "implication_for_us": "Wir müssen schnell reagieren.",
                        "movement_strength": "strong",
                        "source_url": "https://techcrunch.com/workday-ai",
                        "source_domain": "techcrunch.com",
                        "source_title": "TechCrunch – Workday AI",
                    }
                ],
            }
        ],
    )


STATS = {
    "date": "11.06.2026",
    "time": "06:00",
    "sources_total": 5,
    "errors": 1,
    "duration": "2m 30s",
    "digest_generated": False,
}


def test_send_crawl_report_calls_smtp():
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        send_crawl_report(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user="user",
            smtp_password="pass",
            smtp_from="from@example.com",
            recipients=["to@example.com"],
            crawl_stats=STATS,
        )

        mock_smtp_cls.assert_called_once_with("smtp.example.com", 587)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("user", "pass")
        mock_server.send_message.assert_called_once()


def test_send_crawl_report_message_contains_stats():
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        send_crawl_report(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user="",
            smtp_password="",
            smtp_from="from@example.com",
            recipients=["a@b.com", "c@d.com"],
            crawl_stats=STATS,
        )

        msg = mock_server.send_message.call_args[0][0]
        body = msg.get_payload()
        assert "11.06.2026" in body
        assert "5" in body
        assert "2m 30s" in body
        assert msg["Subject"] == "[WFM Intel] Crawl abgeschlossen – 11.06.2026"
        assert "a@b.com" in msg["To"]


def test_send_crawl_report_includes_digest_line_when_generated():
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        stats = {**STATS, "digest_generated": True}
        send_crawl_report(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user="",
            smtp_password="",
            smtp_from="from@example.com",
            recipients=["to@example.com"],
            crawl_stats=stats,
        )

        msg = mock_server.send_message.call_args[0][0]
        assert "Digest" in msg.get_payload()


def test_send_crawl_report_skips_login_when_no_credentials():
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        send_crawl_report(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user="",
            smtp_password="",
            smtp_from="from@example.com",
            recipients=["to@example.com"],
            crawl_stats=STATS,
        )

        mock_server.login.assert_not_called()


def test_send_crawl_report_raises_on_smtp_failure():
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_smtp_cls.side_effect = ConnectionRefusedError("refused")

        with pytest.raises(ConnectionRefusedError):
            send_crawl_report(
                smtp_host="bad-host",
                smtp_port=587,
                smtp_user="",
                smtp_password="",
                smtp_from="from@example.com",
                recipients=["to@example.com"],
                crawl_stats=STATS,
            )


# --- send_digest_email ---

def _call_send_digest_email(mock_server):
    digest = make_test_digest()
    send_digest_email(
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_user="user",
        smtp_password="pass",
        smtp_from="from@example.com",
        recipients=["to@example.com"],
        digest=digest,
        app_base_url="https://wfm.saure.me",
    )


def test_send_digest_email_calls_smtp():
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_server
        _call_send_digest_email(mock_server)
        mock_smtp_cls.assert_called_once_with("smtp.example.com", 587)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("user", "pass")
        mock_server.send_message.assert_called_once()


def test_send_digest_email_subject_contains_week_range():
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_server
        _call_send_digest_email(mock_server)
        msg = mock_server.send_message.call_args[0][0]
        assert "[WFM Intel] Weekly Digest" in msg["Subject"]


def test_send_digest_email_html_contains_digest_content():
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_server
        _call_send_digest_email(mock_server)
        msg = mock_server.send_message.call_args[0][0]
        # multipart: iterate payloads to find HTML part
        html_body = ""
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                html_body = part.get_payload(decode=True).decode()
                break
        assert "Workday" in html_body
        assert "Wettbewerber" in html_body
        assert "KI dominiert" in html_body
        assert "techcrunch.com" in html_body


def test_send_digest_email_html_contains_tool_and_source_links():
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_server
        _call_send_digest_email(mock_server)
        msg = mock_server.send_message.call_args[0][0]
        html_body = ""
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                html_body = part.get_payload(decode=True).decode()
                break
        assert "https://wfm.saure.me/digests" in html_body
        assert "https://wfm.saure.me/digests/test-digest-abc" not in html_body
        assert "https://techcrunch.com/workday-ai" in html_body


def test_send_digest_email_html_contains_logo_when_provided():
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_server
        digest = make_test_digest()
        send_digest_email(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user="",
            smtp_password="",
            smtp_from="from@example.com",
            recipients=["to@example.com"],
            digest=digest,
            app_base_url="https://wfm.saure.me",
            company_logos={"Workday": "https://wfm.saure.me/static/logos/workday.png"},
        )
        msg = mock_server.send_message.call_args[0][0]
        html_body = ""
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                html_body = part.get_payload(decode=True).decode()
                break
        assert "https://wfm.saure.me/static/logos/workday.png" in html_body


def test_send_digest_email_html_contains_signal_count():
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_server
        digest = make_test_digest()
        send_digest_email(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user="",
            smtp_password="",
            smtp_from="from@example.com",
            recipients=["to@example.com"],
            digest=digest,
            app_base_url="https://wfm.saure.me",
            new_signals_count=42,
        )
        msg = mock_server.send_message.call_args[0][0]
        html_body = ""
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                html_body = part.get_payload(decode=True).decode()
                break
        assert "42 Signale" in html_body


def test_send_digest_email_raises_on_smtp_failure():
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_smtp_cls.side_effect = ConnectionRefusedError("refused")
        with pytest.raises(ConnectionRefusedError):
            send_digest_email(
                smtp_host="bad-host",
                smtp_port=587,
                smtp_user="",
                smtp_password="",
                smtp_from="from@example.com",
                recipients=["to@example.com"],
                digest=make_test_digest(),
                app_base_url="https://wfm.saure.me",
            )
