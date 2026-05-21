from __future__ import annotations

from datetime import datetime, time, timezone

from sqlalchemy.orm import Session, joinedload

from app.models.company import Company
from app.models.capability_benchmark import CompetitorCapabilityBenchmark
from app.models.signal_assessment import SignalAssessment
from app.assessor.capabilities import CAPABILITIES, CAPABILITY_KEYS
from app.benchmark.period import get_period_bounds
from app.schemas.benchmark import (
    BenchmarkMatrixCell,
    BenchmarkOverviewResponse,
    BenchmarkSubScores,
    CapabilityAssessmentItem,
    CapabilityAssessmentsResponse,
    CapabilityLeaderboardResponse,
    CompetitorBenchmarkDetail,
    CompetitorBenchmarkResponse,
    CompetitorBrief,
    LeaderboardEntry,
)


class BenchmarkQueryService:
    def __init__(self, db: Session):
        self.db = db

    def get_overview(self, period_type: str = "30d") -> BenchmarkOverviewResponse:
        period_start, period_end = get_period_bounds(period_type)
        competitors = (
            self.db.query(Company).filter(Company.type == "competitor").all()
        )
        benchmarks = (
            self.db.query(CompetitorCapabilityBenchmark)
            .filter_by(period_type=period_type)
            .all()
        )
        lookup: dict[tuple[str, str], CompetitorCapabilityBenchmark] = {
            (b.company_id, b.capability_key): b for b in benchmarks
        }

        # Include all capability keys (no visibility filter) so the list matches CAPABILITY_KEYS
        cap_keys = list(CAPABILITY_KEYS)
        matrix: dict[str, dict[str, BenchmarkMatrixCell]] = {}
        for cap_key in cap_keys:
            matrix[cap_key] = {}
            for c in competitors:
                b = lookup.get((c.id, cap_key))
                if b:
                    matrix[cap_key][c.id] = BenchmarkMatrixCell(
                        score=b.relative_strength_score,
                        tier=b.tier,
                        confidence=b.confidence,
                        rank=b.peer_rank,
                        momentum_score=b.execution_momentum_score,
                    )
                else:
                    matrix[cap_key][c.id] = BenchmarkMatrixCell(
                        score=0,
                        tier="weakly_evidenced",
                        confidence=0.0,
                        rank=None,
                        momentum_score=0,
                    )

        return BenchmarkOverviewResponse(
            period_type=period_type,
            period_start=period_start,
            period_end=period_end,
            capabilities=cap_keys,
            competitors=[CompetitorBrief(id=c.id, name=c.name, slug=c.slug) for c in competitors],
            matrix=matrix,
        )

    def get_competitor_strengths(self, slug: str, period_type: str = "30d") -> CompetitorBenchmarkResponse:
        company = self.db.query(Company).filter_by(slug=slug).first()
        if company is None:
            raise ValueError(f"Company not found: {slug!r}")

        benchmarks = (
            self.db.query(CompetitorCapabilityBenchmark)
            .filter_by(company_id=company.id, period_type=period_type)
            .all()
        )
        lookup = {b.capability_key: b for b in benchmarks}

        details: list[CompetitorBenchmarkDetail] = []
        for cap_key in CAPABILITY_KEYS:
            cap_meta = CAPABILITIES[cap_key]
            b = lookup.get(cap_key)
            if b:
                detail = CompetitorBenchmarkDetail(
                    capability_key=cap_key,
                    label=cap_meta["label"],
                    relative_strength_score=b.relative_strength_score,
                    prev_period_strength_score=b.prev_period_strength_score,
                    strength_delta=b.strength_delta,
                    tier=b.tier,
                    peer_rank=b.peer_rank,
                    peer_percentile=b.peer_percentile,
                    confidence=b.confidence,
                    sub_scores=BenchmarkSubScores(
                        capability_depth=b.capability_depth_score,
                        execution_momentum=b.execution_momentum_score,
                        market_proof=b.market_proof_score,
                        strategic_focus=b.strategic_focus_score,
                        evidence_coverage=b.evidence_coverage_score,
                    ),
                    source_signal_count=b.source_signal_count,
                    summary_reason=b.summary_reason,
                )
            else:
                detail = CompetitorBenchmarkDetail(
                    capability_key=cap_key,
                    label=cap_meta["label"],
                    relative_strength_score=0,
                    prev_period_strength_score=None,
                    strength_delta=None,
                    tier="weakly_evidenced",
                    peer_rank=None,
                    peer_percentile=None,
                    confidence=0.0,
                    sub_scores=BenchmarkSubScores(),
                    source_signal_count=0,
                    summary_reason=None,
                )
            details.append(detail)

        sorted_by_score = sorted(details, key=lambda d: d.relative_strength_score, reverse=True)
        strongest = [d.capability_key for d in sorted_by_score if d.tier in ("leader", "strong")][:3]
        weakest = [d.capability_key for d in sorted_by_score if d.tier == "weakly_evidenced"][:3]

        return CompetitorBenchmarkResponse(
            competitor=CompetitorBrief(id=company.id, name=company.name, slug=company.slug),
            period_type=period_type,
            capabilities=details,
            strongest_capabilities=strongest,
            weakest_evidenced_capabilities=weakest,
        )

    def get_capability_leaderboard(self, cap_key: str, period_type: str = "30d") -> CapabilityLeaderboardResponse:
        benchmarks = (
            self.db.query(CompetitorCapabilityBenchmark)
            .filter_by(capability_key=cap_key, period_type=period_type)
            .order_by(CompetitorCapabilityBenchmark.relative_strength_score.desc())
            .all()
        )
        company_ids = [b.company_id for b in benchmarks]
        companies = {
            c.id: c
            for c in self.db.query(Company).filter(Company.id.in_(company_ids)).all()
        }

        entries: list[LeaderboardEntry] = []
        for i, b in enumerate(benchmarks):
            c = companies.get(b.company_id)
            if not c:
                continue
            entries.append(LeaderboardEntry(
                company_id=b.company_id,
                company_name=c.name,
                slug=c.slug,
                score=b.relative_strength_score,
                tier=b.tier,
                confidence=b.confidence,
                rank=b.peer_rank if b.peer_rank is not None else (i + 1),
                momentum_score=b.execution_momentum_score,
                strength_delta=b.strength_delta,
                summary_reason=b.summary_reason,
            ))

        strongest = entries[0] if entries else None
        risers = [e for e in entries if e.strength_delta is not None and e.strength_delta > 0]
        fastest_riser = max(risers, key=lambda e: e.strength_delta or 0) if risers else None

        cap_meta = CAPABILITIES.get(cap_key, {})
        label = cap_meta["label"] if cap_meta else cap_key

        return CapabilityLeaderboardResponse(
            capability_key=cap_key,
            label=label,
            period_type=period_type,
            leaderboard=entries,
            strongest_competitor=strongest,
            fastest_riser=fastest_riser,
        )

    def get_capability_assessments(
        self, slug: str, cap_key: str, period_type: str = "30d"
    ) -> CapabilityAssessmentsResponse:
        company = self.db.query(Company).filter_by(slug=slug).first()
        if company is None:
            raise ValueError(f"Company not found: {slug!r}")

        period_start, period_end = get_period_bounds(period_type)
        dt_start = datetime.combine(period_start, time.min, tzinfo=timezone.utc)
        dt_end = datetime.combine(period_end, time.max, tzinfo=timezone.utc)

        base_filter = [
            SignalAssessment.company_id == company.id,
            SignalAssessment.capability_primary == cap_key,
            SignalAssessment.created_at >= dt_start,
            SignalAssessment.created_at <= dt_end,
        ]

        total_count = (
            self.db.query(SignalAssessment).filter(*base_filter).count()
        )
        assessments = (
            self.db.query(SignalAssessment)
            .options(joinedload(SignalAssessment.signal))
            .filter(*base_filter)
            .order_by(SignalAssessment.movement_score.desc())
            .limit(20)
            .all()
        )

        cap_meta = CAPABILITIES.get(cap_key, {})
        label = cap_meta.get("label", cap_key) if cap_meta else cap_key

        items = [
            CapabilityAssessmentItem(
                assessment_id=a.id,
                signal_id=a.signal_id,
                title=a.signal.title if a.signal else "—",
                movement_score=a.movement_score or 0,
                signal_class=a.signal_class.value if a.signal_class else "unknown",
                created_at=a.created_at,
            )
            for a in assessments
        ]

        return CapabilityAssessmentsResponse(
            capability_key=cap_key,
            label=label,
            period_type=period_type,
            assessments=items,
            total_count=total_count,
        )
