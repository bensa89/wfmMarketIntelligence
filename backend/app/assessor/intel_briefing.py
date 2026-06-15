import json
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.analyser.client import call_llm
from app.models.signal import Signal
from app.models.signal_assessment import SignalAssessment
from app.models.company import Company
from app.models.context import InternalCompanyContext
from app.models.competitor_summary import CompetitorSummary, PeriodType

logger = logging.getLogger(__name__)


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
        f"Zeitraum: letzte 7 Tage",
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
        "Erstelle exakt dieses Markdown-Dokument. Kein Titel, keine Metadaten, kein Prosa außerhalb der Abschnitte:",
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


def _build_curation_prompt(all_items: list[dict], context: dict) -> str:
    lines = [
        "Du bist ein strategischer Market Intelligence Analyst für ein WFM-Softwareunternehmen.",
        "Unten sind alle Risks, Opportunities und Watchpoints aus den neuesten Competitor-Analysen (letzte 30 Tage).",
        "Wähle jeweils die 4 strategisch wichtigsten Einträge pro Kategorie aus.",
        "",
        f"Unsere Kernkompetenzen: {', '.join(context.get('core_capabilities', []))}",
        f"Strategische Prioritäten: {', '.join(context.get('strategic_priorities', []))}",
        "",
        "Alle Einträge (mit Competitor-Kontext):",
        json.dumps(all_items, ensure_ascii=False, indent=2),
        "",
        "Gib exakt dieses JSON zurück (kein anderer Text):",
        json.dumps({
            "risks": [{"text": "<text>", "signal_ids": ["<id>"], "is_new": True, "company_id": "<id>", "company_name": "<name>", "company_slug": "<slug>"}],
            "opportunities": [{"text": "<text>", "signal_ids": ["<id>"], "is_new": True, "company_id": "<id>", "company_name": "<name>", "company_slug": "<slug>"}],
            "watchpoints": [{"text": "<text>", "signal_ids": ["<id>"], "is_new": True, "company_id": "<id>", "company_name": "<name>", "company_slug": "<slug>"}],
        }, ensure_ascii=False, indent=2),
        "",
        "Regeln:",
        "- Exakt 4 Einträge pro Kategorie (oder weniger wenn nicht genug vorhanden).",
        "- Das Feld 'text' muss auf Deutsch sein. Falls der Input-Text auf Englisch ist, übersetze ihn präzise ins Deutsche.",
        "- signal_ids, is_new, company_id, company_name, company_slug unverändert aus dem Input übernehmen.",
        "- Priorisiere nach strategischer Relevanz für uns (Marktpositionierung, Kundenverlust-Risiko, Differenzierungschancen).",
        "- Keine Duplikate.",
    ]
    return "\n".join(lines)


def _cap_with_coverage(items: list[dict], limit: int = 15) -> list[dict]:
    """Select up to `limit` items while guaranteeing at least one per competitor.
    Prefers is_new=True items for the guaranteed slot, then fills remaining
    capacity in original order."""
    by_company: dict[str, list[dict]] = {}
    for item in items:
        cid = item.get("company_id", "")
        by_company.setdefault(cid, []).append(item)

    # First pass: one item per competitor (prefer is_new)
    selected: list[dict] = []
    remainder: list[dict] = []
    for cid, group in by_company.items():
        new_items = [i for i in group if i.get("is_new")]
        best = (new_items or group)[0]
        selected.append(best)
        remainder.extend(i for i in group if i is not best)

    # Second pass: fill remaining slots in original order
    remaining_slots = limit - len(selected)
    if remaining_slots > 0:
        seen_ids = {id(i) for i in selected}
        for item in items:
            if id(item) not in seen_ids and remaining_slots > 0:
                selected.append(item)
                remaining_slots -= 1

    return selected


def curate_risks_opportunities_watchpoints(db: Session) -> tuple[list, list, list]:
    """Returns (curated_risks, curated_opportunities, curated_watchpoints) as lists of RiskItem dicts."""
    company_ids = (
        db.query(CompetitorSummary.company_id)
        .filter(CompetitorSummary.period_type == PeriodType.thirty_days)
        .distinct()
        .all()
    )

    all_risks: list[dict] = []
    all_opportunities: list[dict] = []
    all_watchpoints: list[dict] = []

    for (cid,) in company_ids:
        company = db.query(Company).filter(Company.id == cid).first()
        if not company:
            continue
        latest = (
            db.query(CompetitorSummary)
            .filter(
                CompetitorSummary.company_id == cid,
                CompetitorSummary.period_type == PeriodType.thirty_days,
            )
            .order_by(CompetitorSummary.created_at.desc())
            .first()
        )
        if not latest:
            continue

        def _enrich(raw: dict | str) -> dict:
            if isinstance(raw, str):
                raw = {"text": raw, "signal_ids": [], "is_new": False}
            return {
                "text": raw.get("text", ""),
                "signal_ids": raw.get("signal_ids") or [],
                "is_new": raw.get("is_new", False),
                "company_id": company.id,
                "company_name": company.name,
                "company_slug": company.slug,
            }

        all_risks.extend(_enrich(r) for r in (latest.top_risks or []) if r)
        all_opportunities.extend(_enrich(o) for o in (latest.top_opportunities or []) if o)
        all_watchpoints.extend(_enrich(w) for w in (latest.watchpoints or []) if w)

    if not any([all_risks, all_opportunities, all_watchpoints]):
        return [], [], []

    all_items = {
        "risks": _cap_with_coverage(all_risks, limit=15),
        "opportunities": _cap_with_coverage(all_opportunities, limit=15),
        "watchpoints": _cap_with_coverage(all_watchpoints, limit=15),
    }
    ctx_record = db.query(InternalCompanyContext).first()
    context = {}
    if ctx_record:
        context = {
            "core_capabilities": ctx_record.core_capabilities or [],
            "strategic_priorities": ctx_record.strategic_priorities or [],
        }

    prompt = _build_curation_prompt(all_items, context)
    try:
        raw = call_llm(prompt, max_tokens=4096, caller="assessor:intel-briefing:curation")
        import re
        raw = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw)
        data = json.loads(raw)
        return data.get("risks", [])[:4], data.get("opportunities", [])[:4], data.get("watchpoints", [])[:4]
    except Exception as e:
        logger.warning("Curation LLM call failed: %s", e)
        return all_risks[:4], all_opportunities[:4], all_watchpoints[:4]


def generate_intelligence_briefing(db: Session) -> tuple[str, int, int]:
    """Returns (content, signal_count, assessment_count)."""
    since = datetime.now(timezone.utc) - timedelta(days=7)

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
    content = call_llm(prompt, max_tokens=2048, caller="assessor:intel-briefing:generate")
    return content, len(signals_data), len(assessments_data)
