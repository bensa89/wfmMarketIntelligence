from __future__ import annotations
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from collections import Counter
from sqlalchemy.orm import Session

from app.models.competitor_scorecard import CompetitorScorecard
from app.models.signal_assessment import SignalAssessment
from app.models.capability_benchmark import CompetitorCapabilityBenchmark
from app.assessor.capabilities import CAPABILITIES
from app.scorecard.constants import (
    DIMENSION_WEIGHTS, PERIOD_DAYS, SCORECARD_VERSION, ROUTING_VERSION,
    RISK_FLAG_STRATEGIC_WEIGHT_THRESHOLD,
)
from app.scorecard.kpi_engine import (
    AssessmentKPIInput, compute_capability_strength_kpis, compute_activity_kpis,
    compute_market_impact_kpis, compute_customer_proof_kpis, compute_momentum_kpis,
    compute_dimension_score, KPIValue,
)

logger = logging.getLogger(__name__)

_KPI_COMPUTERS = {
    "capability_strength": compute_capability_strength_kpis,
    "activity": compute_activity_kpis,
    "market_impact": compute_market_impact_kpis,
    "customer_proof": compute_customer_proof_kpis,
}


class ScorecardBuilder:
    def __init__(self, db: Session):
        self.db = db

    def build(self, company_id: str, period_type: str) -> CompetitorScorecard:
        period_days = PERIOD_DAYS[period_type]
        now = datetime.now(timezone.utc)
        period_end = now
        period_start = now - timedelta(days=period_days)
        prev_end = period_start
        prev_start = prev_end - timedelta(days=period_days)

        assessments = self._fetch(company_id, period_start, period_end)
        prior = self._fetch(company_id, prev_start, prev_end)

        dim_scores: dict[str, dict] = {}
        all_ids = [a.id for a in assessments]

        for dim_key in DIMENSION_WEIGHTS:
            inputs = self._to_kpi_inputs(assessments, dim_key, period_days, now)
            if dim_key == "momentum":
                prior_inputs = self._to_kpi_inputs(prior, dim_key, period_days, prev_end)
                kpis = compute_momentum_kpis(inputs, prior_inputs)
            else:
                kpis = _KPI_COMPUTERS[dim_key](inputs)

            score = compute_dimension_score(dim_key, {k: v for k, v in kpis.items()}) if kpis else None
            trend_kpi = kpis.get("mom_trend")
            trend = trend_kpi.value if trend_kpi else None

            dim_scores[dim_key] = {
                "score": score,
                "trend": trend,
                "kpis": {k: {"value": v.value, "contributing_ids": v.contributing_ids} for k, v in kpis.items()},
            }

        overall, overall_trend = self._compute_overall(dim_scores)
        top_moves = self._top_moves(assessments)
        risk_flags = self._risk_flags(assessments)
        watchpoints = self._watchpoints(assessments)
        top_caps = self._top_capabilities(company_id, period_type)

        # Flip previous current snapshots
        self.db.query(CompetitorScorecard).filter_by(
            company_id=company_id, period_type=period_type, is_current=True
        ).update({"is_current": False})
        self.db.flush()

        scorecard = CompetitorScorecard(
            company_id=company_id,
            period_type=period_type,
            period_start=period_start.date(),
            period_end=period_end.date(),
            generated_at=now,
            overall_score=overall,
            overall_trend=overall_trend,
            dimension_scores=dim_scores,
            top_capabilities=top_caps,
            top_moves=top_moves,
            risk_flags=risk_flags,
            watchpoints=watchpoints,
            benchmark_position=None,
            contributing_assessment_ids=all_ids,
            is_current=True,
            scorecard_version=SCORECARD_VERSION,
            routing_version=ROUTING_VERSION,
        )
        self.db.add(scorecard)
        self.db.commit()

        # Compute benchmark position after insert (uses full snapshot set)
        position = self._benchmark_position(company_id, period_type, scorecard.id)
        scorecard.benchmark_position = position
        self.db.commit()

        return scorecard

    def _fetch(self, company_id: str, start: datetime, end: datetime) -> list[SignalAssessment]:
        from sqlalchemy import func
        effective_from = func.coalesce(SignalAssessment.valid_from, SignalAssessment.created_at)
        return (
            self.db.query(SignalAssessment)
            .filter(
                SignalAssessment.company_id == company_id,
                effective_from <= end,
                (SignalAssessment.valid_until == None) | (SignalAssessment.valid_until >= start),
            )
            .all()
        )

    def _to_kpi_inputs(
        self,
        assessments: list[SignalAssessment],
        dim_key: str,
        period_days: int,
        ref_time: datetime,
    ) -> list[AssessmentKPIInput]:
        result = []
        for a in assessments:
            dim_targets = a.dimension_targets or {}
            if isinstance(dim_targets, list):
                modifier = 1.0 if dim_key in dim_targets else 0.0
            else:
                modifier = dim_targets.get(dim_key, 0.0)
            if modifier == 0.0:
                continue
            valid_from = a.valid_from or a.created_at
            age_days = max(0, (ref_time.replace(tzinfo=None) - valid_from.replace(tzinfo=None)).days)
            result.append(AssessmentKPIInput(
                id=a.id,
                movement_score=a.movement_score or 0,
                movement_strength=(a.movement_strength.value if hasattr(a.movement_strength, "value") else a.movement_strength) or "weak",
                signal_class=(a.signal_class.value if hasattr(a.signal_class, "value") else a.signal_class) or "weak_signal",
                evidence_strength=a.evidence_strength or 3,
                visibility_impact=(a.visibility_impact.value if hasattr(a.visibility_impact, "value") else a.visibility_impact) or "low",
                confidence=a.confidence or 0.5,
                capability_primary=a.capability_primary or "other",
                capability_secondary=a.capability_secondary or [],
                assessment_weight=a.assessment_weight or 1.0,
                dimension_modifier=modifier,
                age_days=age_days,
                period_days=period_days,
            ))
        return result

    def _compute_overall(self, dim_scores: dict) -> tuple[Optional[float], Optional[str]]:
        non_null = {k: v for k, v in dim_scores.items() if v["score"] is not None}
        if not non_null:
            return None, None
        total_raw_weight = sum(DIMENSION_WEIGHTS[k] for k in non_null)
        score = sum(
            v["score"] * DIMENSION_WEIGHTS[k] / total_raw_weight
            for k, v in non_null.items()
        )
        momentum = dim_scores.get("momentum", {}).get("trend")
        return round(score, 2), momentum

    def _top_moves(self, assessments: list[SignalAssessment], n: int = 5) -> list[dict]:
        scored = sorted(
            assessments,
            key=lambda a: (a.movement_score or 0) * (a.assessment_weight or 1.0),
            reverse=True,
        )
        seen_signals: set[str] = set()
        result = []
        for a in scored:
            if a.signal_id in seen_signals:
                continue
            seen_signals.add(a.signal_id)
            sig = a.signal
            published_at = (sig.published_at or sig.created_at) if sig else None
            result.append({
                "assessment_id": a.id,
                "signal_id": a.signal_id,
                "title": sig.title if sig else "",
                "movement_score": a.movement_score or 0,
                "signal_class": (a.signal_class.value if hasattr(a.signal_class, "value") else a.signal_class) or "",
                "published_at": published_at.isoformat() if published_at else None,
            })
            if len(result) >= n:
                break
        return result

    def _risk_flags(self, assessments: list[SignalAssessment]) -> list[dict]:
        result = []
        for a in assessments:
            ms = a.movement_strength.value if hasattr(a.movement_strength, "value") else a.movement_strength
            if ms != "market_shaping":
                continue
            cap = CAPABILITIES.get(a.capability_primary or "", {})
            if cap.get("strategic_weight", 0) >= RISK_FLAG_STRATEGIC_WEIGHT_THRESHOLD:
                result.append({
                    "assessment_id": a.id,
                    "signal_id": a.signal_id,
                    "capability_key": a.capability_primary,
                    "movement_strength": ms,
                    "title": a.signal.title if a.signal else "",
                })
        return result

    def _watchpoints(self, assessments: list[SignalAssessment]) -> list[str]:
        counter: Counter = Counter()
        for a in assessments:
            for item in (a.watch_items or []):
                counter[item.strip()] += 1
        return [item for item, _ in counter.most_common()]

    def _top_capabilities(self, company_id: str, period_type: str, n: int = 5) -> list[dict]:
        rows = (
            self.db.query(CompetitorCapabilityBenchmark)
            .filter_by(company_id=company_id, period_type=period_type)
            .order_by(CompetitorCapabilityBenchmark.relative_strength_score.desc())
            .limit(n)
            .all()
        )
        return [
            {"capability_key": r.capability_key, "score": r.relative_strength_score}
            for r in rows
        ]

    def _benchmark_position(self, company_id: str, period_type: str, this_id: str) -> dict:
        rows = (
            self.db.query(CompetitorScorecard)
            .filter_by(period_type=period_type, is_current=True)
            .all()
        )
        scored = sorted(
            rows,
            key=lambda r: r.overall_score if r.overall_score is not None else -1,
            reverse=True,
        )
        total = len(scored)
        rank = next((i + 1 for i, r in enumerate(scored) if r.id == this_id), total)
        percentile = round(((total - rank) / max(total - 1, 1)) * 100, 1) if total > 1 else 100.0
        return {"rank": rank, "percentile": percentile, "total_competitors": total}
