from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.analyser.client import call_llm
from app.models.signal import Signal
from app.models.signal_assessment import SignalAssessment
from app.models.company import Company
from app.models.context import InternalCompanyContext


def _build_prompt(signals: list, assessments: list, context: dict) -> str:
    company_names = sorted({s["company"] for s in signals})
    strong = [a for a in assessments if a["movement_strength"] in ("market_shaping", "strong")]
    strong.sort(key=lambda a: a["movement_score"] or 0, reverse=True)

    cap_counts: dict[str, int] = {}
    for a in assessments:
        if a["capability_primary"]:
            cap_counts[a["capability_primary"]] = cap_counts.get(a["capability_primary"], 0) + 1
    top_caps = sorted(cap_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    lines = [
        "Du bist ein strategischer Market Intelligence Analyst für ein WFM-Softwareunternehmen.",
        "Analysiere die folgenden Wettbewerbsbewegungen seit dem letzten Crawl und erstelle ein strukturiertes Briefing.",
        "",
        f"Zeitraum: letzte 24 Stunden",
        f"Neue Signale: {len(signals)}",
        f"Bewertete Signale: {len(assessments)}",
        f"Beteiligte Unternehmen: {', '.join(company_names)}",
        "",
    ]

    if context.get("core_capabilities"):
        lines += [
            f"Unsere Kernkompetenzen: {', '.join(context['core_capabilities'])}",
            f"Strategische Prioritäten: {', '.join(context.get('strategic_priorities', []))}",
            "",
        ]

    if strong:
        lines += ["Starke / marktprägende Bewegungen:"]
        for a in strong[:8]:
            lines.append(f"  [{a['company']}] {a['title']}")
            lines.append(f"    Stärke: {a['movement_strength']} | Score: {a['movement_score']} | Capability: {a['capability_primary']}")
            if a["assessment_summary"]:
                lines.append(f"    Assessment: {a['assessment_summary']}")
            if a["implication_for_us"]:
                lines.append(f"    → Für uns: {a['implication_for_us']}")
        lines.append("")

    if top_caps:
        lines += ["Aktivste Capability-Bereiche:"]
        for cap, count in top_caps:
            lines.append(f"  - {cap}: {count} Signale")
        lines.append("")

    lines += [
        "Erstelle exakt dieses Markdown-Dokument (kein Prosa außerhalb der Abschnitte):",
        "",
        "## Strategischer Überblick",
        "[2–3 Sätze: Welche Wettbewerber bewegen sich wie? Was ist die übergeordnete Stoßrichtung?]",
        "",
        "## Handlungsempfehlungen",
        "| Priorität | Signal | Unternehmen | Empfehlung |",
        "|-----------|--------|-------------|------------|",
        "| #1 | ... | ... | ... |",
        "| #2 | ... | ... | ... |",
        "| #3 | ... | ... | ... |",
        "",
        "Maximal 3 Handlungsempfehlungen. Fokus auf konkrete, umsetzbare Maßnahmen für unser Produkt- oder GTM-Team.",
    ]
    return "\n".join(lines)


def generate_intelligence_briefing(db: Session) -> tuple[str, int, int]:
    """Returns (content, signal_count, assessment_count)."""
    since = datetime.now(timezone.utc) - timedelta(hours=24)

    signals_rows = (
        db.query(Signal, Company.name)
        .join(Company, Company.id == Signal.company_id)
        .filter(Signal.created_at >= since)
        .order_by(Signal.created_at.desc())
        .all()
    )

    signal_ids = [s.id for s, _ in signals_rows]
    assessments_rows = (
        db.query(SignalAssessment, Signal.title, Company.name)
        .join(Signal, Signal.id == SignalAssessment.signal_id)
        .join(Company, Company.id == SignalAssessment.company_id)
        .filter(SignalAssessment.signal_id.in_(signal_ids))
        .order_by(SignalAssessment.movement_score.desc().nullslast())
        .all()
    ) if signal_ids else []

    signals_data = [
        {"company": name, "title": s.title}
        for s, name in signals_rows
    ]
    assessments_data = [
        {
            "company": cname,
            "title": title,
            "movement_strength": a.movement_strength.value if a.movement_strength else None,
            "movement_score": a.movement_score,
            "capability_primary": a.capability_primary,
            "assessment_summary": a.assessment_summary,
            "implication_for_us": a.implication_for_us,
        }
        for a, title, cname in assessments_rows
    ]

    ctx_record = db.query(InternalCompanyContext).first()
    context = {}
    if ctx_record:
        context = {
            "core_capabilities": ctx_record.core_capabilities or [],
            "strategic_priorities": ctx_record.strategic_priorities or [],
        }

    prompt = _build_prompt(signals_data, assessments_data, context)
    content = call_llm(prompt, max_tokens=2048)
    return content, len(signals_data), len(assessments_data)
