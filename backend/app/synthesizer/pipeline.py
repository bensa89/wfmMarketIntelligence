import json
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.company import Company, CompanyType
from app.models.signal import Signal
from app.models.external_company_view import ExternalCompanyView
from app.analyser.client import call_llm
from app.synthesizer.prompts import build_synthesis_prompt

logger = logging.getLogger(__name__)

_MAX_SIGNALS = 100


def run_synthesis(db: Session) -> ExternalCompanyView:
    own_companies = db.query(Company).filter_by(type=CompanyType.own_company).all()
    own_company_ids = [c.id for c in own_companies]

    if not own_company_ids:
        logger.warning("run_synthesis — no company with type 'own_company' found")
        raise ValueError("No company with type 'own_company' found")

    company_names = [c.name for c in own_companies]
    signals = (
        db.query(Signal)
        .filter(Signal.company_id.in_(own_company_ids))
        .order_by(Signal.created_at.desc())
        .limit(_MAX_SIGNALS)
        .all()
    )

    if not signals:
        logger.warning(
            "run_synthesis — no signals found for own_company [companies=%s]",
            company_names,
        )
        raise ValueError("No signals found for own_company — crawl the company first")

    logger.info(
        "run_synthesis — starting synthesis [companies=%s signals=%d]",
        company_names,
        len(signals),
    )

    signal_dicts = [
        {
            "title": s.title,
            "topic": s.topic,
            "summary": s.summary,
            "why_it_matters": s.why_it_matters,
        }
        for s in signals
    ]

    prompt = build_synthesis_prompt(signal_dicts)
    raw = call_llm(prompt, caller="synthesizer:external-view")

    try:
        data = json.loads(raw.strip())
    except json.JSONDecodeError:
        import re
        logger.warning("run_synthesis — LLM response not valid JSON, attempting regex extraction")
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            logger.error("run_synthesis — could not extract JSON from LLM response: %r", raw[:200])
            raise ValueError(f"LLM returned invalid JSON: {raw[:200]}")
        data = json.loads(match.group())

    view = db.query(ExternalCompanyView).first()
    is_update = view is not None
    now = datetime.now(timezone.utc)

    if view is None:
        view = ExternalCompanyView(
            summary=data.get("summary"),
            key_messages=data.get("key_messages", []),
            observed_capabilities=data.get("observed_capabilities", []),
            observed_differentiators=data.get("observed_differentiators", []),
            observed_target_markets=data.get("observed_target_markets", []),
            tone_and_positioning=data.get("tone_and_positioning"),
            signal_count_used=len(signals),
            generated_at=now,
            updated_at=now,
        )
        db.add(view)
    else:
        view.summary = data.get("summary")
        view.key_messages = data.get("key_messages", [])
        view.observed_capabilities = data.get("observed_capabilities", [])
        view.observed_differentiators = data.get("observed_differentiators", [])
        view.observed_target_markets = data.get("observed_target_markets", [])
        view.tone_and_positioning = data.get("tone_and_positioning")
        view.signal_count_used = len(signals)
        view.generated_at = now
        view.updated_at = now

    db.commit()
    db.refresh(view)

    logger.info(
        "ExternalCompanyView %s [id=%s signals=%d key_messages=%d capabilities=%d]",
        "updated" if is_update else "created",
        view.id,
        len(signals),
        len(view.key_messages or []),
        len(view.observed_capabilities or []),
    )
    return view
