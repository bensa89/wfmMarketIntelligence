from __future__ import annotations
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.models.company import Company
from app.models.signal_assessment import SignalAssessment
from app.models.capability_benchmark import CompetitorCapabilityBenchmark
from app.assessor.capabilities import CAPABILITY_KEYS
from app.benchmark.period import get_period_bounds
from app.benchmark.scoring import (
    compute_sub_scores,
    compute_relative_strength,
    determine_tier,
    compute_confidence,
)


class BenchmarkAggregationService:
    def __init__(self, db: Session):
        self.db = db

    def recompute_all(self, period_type: str = "30d") -> list[CompetitorCapabilityBenchmark]:
        competitors = (
            self.db.query(Company).filter(Company.type == "competitor").all()
        )
        results = []
        for c in competitors:
            results.extend(self.recompute_company(c.id, period_type))
        self._compute_peer_rankings(period_type)
        return results

    def recompute_company(
        self, company_id: str, period_type: str = "30d"
    ) -> list[CompetitorCapabilityBenchmark]:
        period_start, period_end = get_period_bounds(period_type)
        # Convert date bounds to datetime for correct comparison against DateTime column
        dt_start = datetime(period_start.year, period_start.month, period_start.day, 0, 0, 0)
        dt_end = datetime(period_end.year, period_end.month, period_end.day, 23, 59, 59)
        all_assessments = (
            self.db.query(SignalAssessment)
            .filter(
                SignalAssessment.company_id == company_id,
                SignalAssessment.created_at >= dt_start,
                SignalAssessment.created_at <= dt_end,
            )
            .all()
        )

        benchmarks: list[CompetitorCapabilityBenchmark] = []
        for cap_key in CAPABILITY_KEYS:
            cap_assessments = [
                a for a in all_assessments if a.capability_primary == cap_key
            ]
            scores = compute_sub_scores(
                cap_assessments, all_assessments, period_start, period_end, cap_key
            )
            confidence = compute_confidence(cap_assessments, scores.evidence_coverage)
            strength_score = compute_relative_strength(scores)
            tier = determine_tier(strength_score, confidence, scores.evidence_coverage)

            prev_score = self._get_previous_score(company_id, cap_key, period_type)
            delta = (strength_score - prev_score) if prev_score is not None else None

            benchmark = self._upsert(
                company_id=company_id,
                capability_key=cap_key,
                period_type=period_type,
                period_start=period_start,
                period_end=period_end,
                scores=scores,
                strength_score=strength_score,
                prev_score=prev_score,
                delta=delta,
                tier=tier,
                confidence=confidence,
                signal_count=len(cap_assessments),
            )
            benchmarks.append(benchmark)

        self.db.commit()
        return benchmarks

    def _get_previous_score(
        self, company_id: str, cap_key: str, period_type: str
    ) -> int | None:
        existing = (
            self.db.query(CompetitorCapabilityBenchmark)
            .filter_by(company_id=company_id, capability_key=cap_key, period_type=period_type)
            .first()
        )
        return existing.relative_strength_score if existing else None

    def _upsert(
        self, *, company_id, capability_key, period_type, period_start, period_end,
        scores, strength_score, prev_score, delta, tier, confidence, signal_count,
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
