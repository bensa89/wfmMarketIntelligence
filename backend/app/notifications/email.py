import html
import smtplib
import logging
from email.message import EmailMessage
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.digest import WeeklyDigest

logger = logging.getLogger(__name__)

_MONTHS_DE = [
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
]

_MOVEMENT_LABELS = {
    "strong":   ("⬆ Starke Bewegung",  "#fef2f2", "#dc2626"),
    "moderate": ("⬆ Mäßige Bewegung",  "#fefce8", "#854d0e"),
    "weak":     ("➡ Schwache Bewegung", "#f8fafc", "#64748b"),
}


def _smtp_send(smtp_host, smtp_port, smtp_user, smtp_password, msg):
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.ehlo()
        if smtp_port != 25:
            server.starttls()
        if smtp_user and smtp_password:
            server.login(smtp_user, smtp_password)
        server.send_message(msg)


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
    msg["From"] = f"WFM Intelligence Hub <{smtp_from}>"
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

    _smtp_send(smtp_host, smtp_port, smtp_user, smtp_password, msg)


def send_digest_email(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    smtp_from: str,
    recipients: List[str],
    digest: "WeeklyDigest",
    app_base_url: str,
    company_logos: Optional[Dict[str, str]] = None,
    new_signals_count: int = 0,
) -> None:
    week_start = digest.week_start
    week_end = digest.week_end
    date_range = (
        f"{week_start.day:02d}. – "
        f"{week_end.day:02d}. {_MONTHS_DE[week_end.month - 1]} {week_end.year}"
    )
    digest_url = f"{app_base_url}/digests"
    sections = digest.sections or []

    msg = EmailMessage()
    msg["Subject"] = f"[WFM Intel] Weekly Digest – {date_range}"
    msg["From"] = f"WFM Intelligence Hub <{smtp_from}>"
    msg["To"] = ", ".join(recipients)

    msg.set_content(_build_plain_text(digest, date_range, digest_url, sections, new_signals_count))
    msg.add_alternative(
        _build_html(digest, date_range, digest_url, sections, app_base_url, company_logos or {}, new_signals_count),
        subtype="html",
    )

    _smtp_send(smtp_host, smtp_port, smtp_user, smtp_password, msg)


def _build_plain_text(digest, date_range: str, digest_url: str, sections: list, signal_count: int) -> str:
    signal_label = "1 Signal" if signal_count == 1 else f"{signal_count} Signale"
    lines = [
        "WFM Market Intelligence Hub – Weekly Digest",
        f"Zeitraum: {date_range}  |  {signal_label}",
        "",
    ]
    if digest.summary:
        lines += [digest.summary, ""]
    for section in sections:
        lines += [f"== {section['title']} ==", ""]
        for item in section.get("items", []):
            lines += [
                f"[{item['company']}] {item['title']}",
                item.get("narrative", ""),
            ]
            if item.get("implication_for_us"):
                lines += [f"Implikation: {item['implication_for_us']}"]
            if item.get("source_url"):
                lines += [f"Quelle: {item['source_url']}"]
            lines += [""]
    lines += [f"Im Tool öffnen: {digest_url}"]
    return "\n".join(lines)


def _render_items(items: list, company_logos: dict) -> str:
    parts = []
    for i, item in enumerate(items):
        border = "border-bottom:1px solid #f1f5f9;" if i < len(items) - 1 else ""
        company = html.escape(item.get("company", ""))
        title = html.escape(item.get("title", ""))
        narrative = html.escape(item.get("narrative", ""))
        implication = html.escape(item.get("implication_for_us") or "")
        source_url = item.get("source_url") or ""
        source_title = html.escape(item.get("source_title") or item.get("source_domain") or source_url)
        strength = item.get("movement_strength")

        logo_img = ""
        logo_url = company_logos.get(item.get("company", ""))
        if logo_url:
            logo_img = (
                f'<img src="{html.escape(logo_url)}" width="18" height="18" '
                f'style="border-radius:3px;object-fit:contain;vertical-align:middle;'
                f'margin-right:6px;display:inline-block;" alt="{company}">'
            )

        strength_badge = ""
        if strength and strength in _MOVEMENT_LABELS:
            label, bg, color = _MOVEMENT_LABELS[strength]
            strength_badge = (
                f'<td style="padding-left:8px;">'
                f'<span style="background:{bg};color:{color};font-size:10px;font-weight:600;'
                f'padding:3px 8px;border-radius:4px;">{label}</span></td>'
            )

        implication_block = ""
        if implication:
            implication_block = f"""
            <table cellpadding="0" cellspacing="0" style="margin-bottom:12px;width:100%;">
              <tr>
                <td style="background:#f0fdf4;border-left:3px solid #22c55e;padding:10px 14px;border-radius:0 6px 6px 0;">
                  <p style="margin:0;color:#15803d;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px;">Implikation für uns</p>
                  <p style="margin:0;color:#166534;font-size:12px;line-height:1.5;">{implication}</p>
                </td>
              </tr>
            </table>"""

        source_link = ""
        if source_url:
            source_link = (
                f'<a href="{html.escape(source_url)}" style="color:#2563eb;font-size:12px;'
                f'text-decoration:none;font-weight:500;">↗ {source_title}</a>'
            )

        parts.append(f"""
        <tr>
          <td style="padding-top:20px;padding-bottom:20px;{border}">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr><td>
                <table cellpadding="0" cellspacing="0" style="margin-bottom:10px;">
                  <tr>
                    <td style="font-size:12px;font-weight:700;color:#374151;white-space:nowrap;">{logo_img}{company}</td>
                    {strength_badge}
                  </tr>
                </table>
                <h3 style="margin:0 0 8px;color:#0f172a;font-size:15px;font-weight:600;line-height:1.4;">{title}</h3>
                <p style="margin:0 0 10px;color:#475569;font-size:13px;line-height:1.65;">{narrative}</p>
                {implication_block}
                {source_link}
              </td></tr>
            </table>
          </td>
        </tr>""")
    return "\n".join(parts)


def _render_sections(sections: list, company_logos: dict) -> str:
    parts = []
    for section in sections:
        title = html.escape(section.get("title", ""))
        items_html = _render_items(section.get("items", []), company_logos)
        parts.append(f"""
        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:32px;">
          <tr>
            <td style="padding-bottom:14px;border-bottom:2px solid #f1f5f9;">
              <h2 style="margin:0;color:#0f172a;font-size:13px;font-weight:700;letter-spacing:0.04em;text-transform:uppercase;">{title}</h2>
            </td>
          </tr>
          {items_html}
        </table>""")
    return "\n".join(parts)


def _build_html(
    digest,
    date_range: str,
    digest_url: str,
    sections: list,
    app_base_url: str,
    company_logos: dict,
    signal_count: int = 0,
) -> str:
    summary = html.escape(digest.summary or "")
    sections_html = _render_sections(sections, company_logos)
    digest_url_escaped = html.escape(digest_url)
    app_url_escaped = html.escape(app_base_url)
    signal_label = "1 Signal" if signal_count == 1 else f"{signal_count} Signale"

    return f"""<!DOCTYPE html>
<html lang="de">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:32px 16px;">
  <tr><td align="center">
    <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

      <tr>
        <td style="background:#0f172a;border-radius:12px 12px 0 0;padding:32px 40px;">
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td>
                <p style="margin:0;color:#94a3b8;font-size:11px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;">Market Intelligence Hub</p>
                <h1 style="margin:8px 0 0;color:#f8fafc;font-size:22px;font-weight:700;letter-spacing:-0.01em;">Weekly Digest</h1>
                <p style="margin:6px 0 0;color:#64748b;font-size:13px;">{date_range}</p>
              </td>
              <td align="right" valign="top">
                <a href="{digest_url_escaped}" style="display:inline-block;background:#1e293b;color:#94a3b8;font-size:11px;font-weight:500;text-decoration:none;padding:7px 14px;border-radius:6px;border:1px solid #334155;">Im Tool öffnen →</a>
              </td>
            </tr>
          </table>
        </td>
      </tr>

      <tr>
        <td style="background:#1e293b;padding:20px 40px 24px;">
          <p style="margin:0;color:#cbd5e1;font-size:14px;line-height:1.65;">{summary}</p>
          <p style="margin:12px 0 0;color:#475569;font-size:12px;">{signal_label} diese Woche</p>
        </td>
      </tr>

      <tr><td style="background:#0f172a;height:1px;font-size:0;line-height:0;">&nbsp;</td></tr>

      <tr>
        <td style="background:#ffffff;padding:32px 40px;border-radius:0 0 12px 12px;">
          {sections_html}

          <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:28px;">
            <tr><td align="center">
              <a href="{digest_url_escaped}" style="display:inline-block;background:#2563eb;color:#ffffff;font-size:14px;font-weight:600;text-decoration:none;padding:12px 28px;border-radius:8px;letter-spacing:-0.01em;">Digest öffnen →</a>
            </td></tr>
          </table>

          <table width="100%" cellpadding="0" cellspacing="0" style="border-top:1px solid #f1f5f9;padding-top:20px;">
            <tr><td>
              <p style="margin:0;color:#94a3b8;font-size:11px;text-align:center;line-height:1.6;">
                WFM Market Intelligence Hub · <a href="{app_url_escaped}" style="color:#94a3b8;">{app_url_escaped}</a>
              </p>
            </td></tr>
          </table>
        </td>
      </tr>

    </table>
  </td></tr>
</table>
</body>
</html>"""
