from __future__ import annotations
import math
from datetime import date, datetime, timezone
from sqlalchemy.orm import Session
from app.models.company import Company
from app.models.signal_assessment import SignalAssessment
from app.models.capability_benchmark import CompetitorCapabilityBenchmark
from app.assessor.capabilities import CAPABILITY_KEYS
from app.benchmark.scoring import (
    compute_sub_scores,
    compute_relative_strength,
    determine_tier,
    compute_confidence,
)

# Half-life per period: 30d → strong recency emphasis, 180d → near-flat (historical view)
_DECAY_LAMBDA = {
    "30d": math.log(2) / 30,
    "90d": math.log(2) / 90,
    "180d": math.log(2) / 180,
}


def _assessment_weight(assessment, lambda_val: float, today: date) -> float:
    created = assessment.created_at
    if hasattr(created, "date"):
        created = created.date()
    age_days = max(0, (today - created).days)
    return math.exp(-lambda_val * age_days)


class BenchmarkAggregationService:
    def __init__(self, db: Session):
        self.db = db

    def recompute_all(self, period_type: str = "180d") -> list[CompetitorCapabilityBenchmark]:
        competitors = (
            self.db.query(Company).filter(Company.type.in_(["competitor", "own_company"])).all()
        )
        results = []
        for c in competitors:
            results.extend(self.recompute_company(c.id, period_type))
        self._compute_peer_rankings(period_type)
        return results

    def recompute_company(
        self, company_id: str, period_type: str = "180d"
    ) -> list[CompetitorCapabilityBenchmark]:
        today = date.today()
        lambda_val = _DECAY_LAMBDA.get(period_type, _DECAY_LAMBDA["180d"])

        # Fetch ALL assessments — no hard time cutoff, decay weights handle recency
        all_assessments = (
            self.db.query(SignalAssessment)
            .filter(SignalAssessment.company_id == company_id)
            .all()
        )
        all_weights = [_assessment_weight(a, lambda_val, today) for a in all_assessments]

        benchmarks: list[CompetitorCapabilityBenchmark] = []
        for cap_key in CAPABILITY_KEYS:
            indices = [i for i, a in enumerate(all_assessments) if a.capability_primary == cap_key]
            cap_assessments = [all_assessments[i] for i in indices]
            cap_weights = [all_weights[i] for i in indices]

            scores = compute_sub_scores(
                cap_assessments, all_assessments,
                period_start=today, period_end=today,
                cap_key=cap_key,
                weights=cap_weights,
                all_weights=all_weights,
            )
            confidence = compute_confidence(cap_assessments, scores.evidence_coverage, cap_weights)
            strength_score = compute_relative_strength(scores)
            tier = determine_tier(strength_score, confidence, scores.evidence_coverage)

            prev_score, prev_momentum = self._get_previous_scores(company_id, cap_key, period_type)
            delta = (strength_score - prev_score) if prev_score is not None else None
            momentum_delta = (scores.execution_momentum - prev_momentum) if prev_momentum is not None else None

            benchmark = self._upsert(
                company_id=company_id,
                capability_key=cap_key,
                period_type=period_type,
                period_start=today,
                period_end=today,
                scores=scores,
                strength_score=strength_score,
                prev_score=prev_score,
                delta=delta,
                prev_momentum=prev_momentum,
                momentum_delta=momentum_delta,
                tier=tier,
                confidence=confidence,
                signal_count=len(cap_assessments),
            )
            benchmarks.append(benchmark)

        self.db.commit()
        return benchmarks

    def _get_previous_scores(
        self, company_id: str, cap_key: str, period_type: str
    ) -> tuple[int | None, int | None]:
        existing = (
            self.db.query(CompetitorCapabilityBenchmark)
            .filter_by(company_id=company_id, capability_key=cap_key, period_type=period_type)
            .first()
        )
        if existing is None:
            return None, None
        return existing.relative_strength_score, existing.execution_momentum_score

    def _upsert(
        self, *, company_id, capability_key, period_type, period_start, period_end,
        scores, strength_score, prev_score, delta, prev_momentum, momentum_delta,
        tier, confidence, signal_count,
    ) -> CompetitorCapabilityBenchmark:
        existing = (
            self.db.query(CompetitorCapabilityBenchmark)
            .filter_by(company_id=company_id, capability_key=capability_key, period_type=period_type)
            .first()
        )
        if existing is None:
            existing = CompetitorCapabilityBenchmark(
                company_id=company_id,
                capability_key=capability_key,
                period_type=period_type,
            )
            self.db.add(existing)

        existing.period_start = period_start
        existing.period_end = period_end
        existing.capability_depth_score = scores.capability_depth
        existing.execution_momentum_score = scores.execution_momentum
        existing.market_proof_score = scores.market_proof
        existing.strategic_focus_score = scores.strategic_focus
        existing.evidence_coverage_score = scores.evidence_coverage
        existing.relative_strength_score = strength_score
        existing.prev_period_strength_score = prev_score
        existing.strength_delta = delta
        existing.prev_period_momentum_score = prev_momentum
        existing.momentum_delta = momentum_delta
        existing.tier = tier
        existing.confidence = confidence
        existing.source_signal_count = signal_count
        existing.updated_at = datetime.now(timezone.utc)
        return existing

    def _compute_peer_rankings(self, period_type: str) -> None:
        for cap_key in CAPABILITY_KEYS:
            benchmarks = (
                self.db.query(CompetitorCapabilityBenchmark)
                .filter_by(capability_key=cap_key, period_type=period_type)
                .order_by(CompetitorCapabilityBenchmark.relative_strength_score.desc())
                .all()
            )
            total = len(benchmarks)
            for i, b in enumerate(benchmarks):
                b.peer_rank = i + 1
                b.peer_percentile = round((1 - i / total) * 100, 1) if total > 0 else 0.0
        self.db.commit()
