from __future__ import annotations
import logging
import math
from datetime import datetime, timezone
from typing import Optional
from collections import Counter
from sqlalchemy.orm import Session

from app.models.competitor_scorecard import CompetitorScorecard
from app.models.signal_assessment import SignalAssessment
from app.models.capability_benchmark import CompetitorCapabilityBenchmark
from app.assessor.capabilities import CAPABILITIES
from app.scorecard.constants import (
    DIMENSION_WEIGHTS, DECAY_LAMBDA, MOMENTUM_WINDOW_DAYS, SCORECARD_VERSION,
    ROUTING_VERSION, RISK_FLAG_STRATEGIC_WEIGHT_THRESHOLD,
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
        lambda_val = DECAY_LAMBDA[period_type]
        now = datetime.now(timezone.utc)

        # Fetch ALL assessments — no hard date cutoff
        assessments = self._fetch_all(company_id)

        # Two decay weight sets: T=0 (now) and T=-N (prior reference for momentum)
        weights_now = self._decay_weights(assessments, lambda_val, now, shift_days=0)
        weights_prior = self._decay_weights(assessments, lambda_val, now, shift_days=MOMENTUM_WINDOW_DAYS)

        dim_scores: dict[str, dict] = {}
        all_ids = [a.id for a in assessments]

        for dim_key in DIMENSION_WEIGHTS:
            inputs_now = self._to_kpi_inputs(assessments, dim_key, weights_now)
            if dim_key == "momentum":
                # Prior inputs: only assessments that existed MOMENTUM_WINDOW_DAYS ago
                inputs_prior = self._to_kpi_inputs(assessments, dim_key, weights_prior)
                inputs_prior = [i for i in inputs_prior if i.decay_weight > 0]
                kpis = compute_momentum_kpis(inputs_now, inputs_prior)
            else:
                kpis = _KPI_COMPUTERS[dim_key](inputs_now)

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

        self.db.query(CompetitorScorecard).filter_by(
            company_id=company_id, period_type=period_type, is_current=True
        ).update({"is_current": False})
        self.db.flush()

        today = now.date()
        scorecard = CompetitorScorecard(
            company_id=company_id,
            period_type=period_type,
            period_start=today,
            period_end=today,
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

        position = self._benchmark_position(company_id, period_type, scorecard.id)
        scorecard.benchmark_position = position
        self.db.commit()

        return scorecard

    def _fetch_all(self, company_id: str) -> list[SignalAssessment]:
        return (
            self.db.query(SignalAssessment)
            .filter(SignalAssessment.company_id == company_id)
            .all()
        )

    def _decay_weights(
        self,
        assessments: list[SignalAssessment],
        lambda_val: float,
        now: datetime,
        shift_days: int,
    ) -> list[float]:
        """
        Compute e^(-λ * effective_age) for each assessment.
        shift_days > 0 simulates standing 'shift_days' days in the past:
          - assessments newer than shift_days have weight 0 (didn't exist yet)
          - older assessments use (age - shift_days) as their effective age
        """
        weights = []
        for a in assessments:
            ref = a.valid_from or a.created_at
            age_days = max(0, (now.replace(tzinfo=None) - ref.replace(tzinfo=None)).days)
            if shift_days > 0:
                if age_days < shift_days:
                    weights.append(0.0)
                    continue
                effective_age = age_days - shift_days
            else:
                effective_age = age_days
            weights.append(math.exp(-lambda_val * effective_age))
        return weights

    def _to_kpi_inputs(
        self,
        assessments: list[SignalAssessment],
        dim_key: str,
        weights: list[float],
    ) -> list[AssessmentKPIInput]:
        result = []
        for a, decay_weight in zip(assessments, weights):
            dim_targets = a.dimension_targets or {}
            if isinstance(dim_targets, list):
                modifier = 1.0 if dim_key in dim_targets else 0.0
            else:
                modifier = dim_targets.get(dim_key, 0.0)
            if modifier == 0.0:
                continue
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
                decay_weight=decay_weight,
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
                "assessed_at": a.created_at.isoformat() if a.created_at else None,
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
