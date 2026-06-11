import pytest
from unittest.mock import patch, MagicMock, call
from app.notifications.email import send_crawl_report


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
