---
title: Automatisierter Digest-E-Mail-Versand
date: 2026-06-11
status: approved
---

# Digest E-Mail-Versand

## Ziel

Nach jeder automatischen Digest-Generierung (standalone oder post-crawl) wird eine gestylte HTML-Mail mit dem vollständigen Digest-Inhalt an konfigurierte Empfänger verschickt. Ziel: iCloud-Postfach des Benutzers.

## Scope

- Digest-E-Mail (neu) — vollständiger HTML-Inhalt mit Sections, Items, Links
- Crawl-Report-E-Mail (bereits vorhanden) — bleibt unverändert
- Beide nutzen dieselbe SMTP-Konfiguration und denselben `email_enabled`-Toggle
- Neuer Test-Button im Frontend sendet den zuletzt generierten Digest per Mail

## Nicht im Scope

- Separate `digest_email_enabled`-Steuerung (ein Toggle für beide Mail-Typen)
- Neue DB-Migration (alle SMTP-Felder existieren bereits)

---

## Backend

### 1. `backend/app/config.py`

Neues Feld:

```python
APP_BASE_URL: str = "https://wfm.saure.me"
```

Wird aus `.env` gelesen. Default entspricht der Produktiv-URL.

### 2. `backend/app/notifications/email.py`

Neue Funktion:

```python
def send_digest_email(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    smtp_from: str,
    recipients: List[str],
    digest: WeeklyDigest,
    app_base_url: str,
) -> None
```

- Rendert HTML-Template als Python f-string (kein Jinja2)
- Sendet als `MIMEMultipart("alternative")` mit Plain-Text-Fallback und HTML-Part
- HTML-Design: dunkler Header (Wochenzeitraum + "Im Tool öffnen"-Link), Intro-Summary, Sections mit farbigen Badges, pro Item: Unternehmens-Badge, Bewegungsstärke, Titel, Narrativ, grüner Implikations-Block, Quellenlink, CTA-Button zum Digest, Footer
- Link zum Digest: `{app_base_url}/digests/{digest.id}`
- Link zu Quellen: `item["source_url"]` direkt aus `digest.sections[].items[]`
- Plain-Text-Fallback: Summary + pro Section/Item: Titel, Narrativ, Quellenlink

### 3. `backend/app/scheduler.py`

**`scheduled_digest_job()`** — Erweiterung:

```python
def scheduled_digest_job() -> None:
    # bestehend: generate_digest(db)
    # neu: nach Generierung
    if config and config.email_enabled and config.email_recipients:
        send_digest_email(...)
```

Config wird wie in `scheduled_crawl_job()` aus DB geladen.

**`scheduled_crawl_job()`** — Erweiterung:

Nach dem bestehenden Block "Post-crawl digest generated":

```python
if digest_generated and config.email_enabled and config.email_recipients:
    send_digest_email(...)  # zusätzlich zur Crawl-Report-Mail
```

Der Crawl-Report enthält weiterhin die Zeile "Weekly Digest wurde automatisch generiert." — die Digest-Mail kommt als separate zweite Mail.

### 4. `backend/app/routers/schedule.py`

Neuer Endpoint:

```
POST /api/schedule/test-digest-email
```

- Lädt den zuletzt generierten `WeeklyDigest` (ORDER BY `generated_at DESC`, LIMIT 1)
- Wenn kein Digest vorhanden: HTTP 400 "Kein Digest vorhanden"
- Wenn keine Empfänger konfiguriert: HTTP 400 "Keine Empfänger konfiguriert"
- Sendet via `send_digest_email()` und gibt `{"status": "sent", "digest_id": "...", "recipients": [...]}` zurück

---

## Frontend

### `frontend/src/pages/ScheduleAdmin.tsx`

Im Block "E-Mail-Benachrichtigungen", unterhalb des bestehenden "Test-E-Mail senden"-Buttons:

- Neuer Button **"Test Digest-E-Mail senden"** mit eigenem Ladezustand (`testDigestEmailLoading`)
- Ruft `POST /schedule/test-digest-email` auf
- Erfolgs-Toast: "Test Digest-E-Mail gesendet"
- Fehler-Toast: Backend-Fehlermeldung (z.B. "Kein Digest vorhanden")
- Beide Buttons nebeneinander oder untereinander — keine Layout-Änderungen sonst

---

## Datenstruktur Digest-Item (zur Referenz)

```json
{
  "signal_id": "uuid",
  "company": "Workday",
  "title": "Workday kündigt KI-Planungsassistent an",
  "narrative": "...",
  "implication_for_us": "...",
  "movement_strength": "strong|moderate|weak|null",
  "source_url": "https://techcrunch.com/...",
  "source_domain": "techcrunch.com",
  "source_title": "TechCrunch – Workday AI Announcement"
}
```

`movement_strength`-Mapping für E-Mail-Anzeige:
- `strong` → "⬆ Starke Bewegung" (rot)
- `moderate` → "⬆ Mäßige Bewegung" (gelb)
- `weak` → "➡ Schwache Bewegung" (grau)
- `null` → kein Badge

---

## SMTP-Konfiguration für iCloud

iCloud benötigt ein App-spezifisches Passwort (2FA):
- Host: `smtp.mail.me.com`
- Port: `587` (STARTTLS)
- User: Apple-ID (z.B. `benjamin@saure.me`)
- Password: App-spezifisches Passwort aus appleid.apple.com

---

## Fehlerbehandlung

- SMTP-Fehler in `scheduled_digest_job()` und `scheduled_crawl_job()`: `logger.warning(...)`, kein Re-Raise (Digest-Generierung gilt trotzdem als erfolgreich)
- Test-Endpoints: SMTP-Fehler als HTTP 400 mit Fehlermeldung zurückgeben

---

## Dateien die sich ändern

| Datei | Änderung |
|---|---|
| `backend/app/config.py` | `APP_BASE_URL` hinzufügen |
| `backend/app/notifications/email.py` | `send_digest_email()` hinzufügen |
| `backend/app/scheduler.py` | Digest-Mail in beide Job-Funktionen einbauen |
| `backend/app/routers/schedule.py` | `POST /test-digest-email` Endpoint |
| `frontend/src/pages/ScheduleAdmin.tsx` | Test-Digest-Mail-Button |
