"""One-time backfill: generate SignalAssessment for all existing signals above threshold.

Usage:
    cd backend
    python scripts/backfill_assessments.py [--threshold 0.4] [--batch-size 20] [--dry-run]
"""
import sys
import os
import argparse
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Backfill SignalAssessments")
    parser.add_argument("--threshold", type=float, default=None,
                        help="Override ASSESSMENT_THRESHOLD (default: from config)")
    parser.add_argument("--batch-size", type=int, default=20, dest="batch_size")
    parser.add_argument("--dry-run", action="store_true", dest="dry_run",
                        help="Report how many signals would be processed, don't call LLM")
    args = parser.parse_args()

    from app.config import settings
    from app.database import SessionLocal
    from app.models.signal import Signal
    from app.models.signal_assessment import SignalAssessment
    from app.assessor.pipeline import assess_signal

    threshold = args.threshold if args.threshold is not None else settings.assessment_threshold
    logger.info("Starting backfill with threshold=%.2f, batch_size=%d, dry_run=%s",
                threshold, args.batch_size, args.dry_run)

    db = SessionLocal()
    try:
        already_assessed = db.query(SignalAssessment.signal_id).scalar_subquery()
        signals_to_process = (
            db.query(Signal)
            .filter(
                Signal.relevance_score >= threshold,
                ~Signal.id.in_(already_assessed),
            )
            .order_by(Signal.created_at.desc())
            .all()
        )

        total = len(signals_to_process)
        logger.info("Found %d signals to assess", total)

        if args.dry_run:
            logger.info("Dry run — exiting without processing")
            return

        processed = 0
        failed = 0
        for i, signal in enumerate(signals_to_process):
            try:
                from sqlalchemy.orm import selectinload
                signal = (
                    db.query(Signal)
                    .options(selectinload(Signal.company), selectinload(Signal.document))
                    .filter(Signal.id == signal.id)
                    .first()
                )
                result = assess_signal(signal, db)
                if result:
                    processed += 1
                else:
                    failed += 1
                if (i + 1) % args.batch_size == 0:
                    logger.info("Progress: %d/%d (failed: %d)", i + 1, total, failed)
            except Exception as e:
                logger.error("Error processing signal %s: %s", signal.id, e)
                failed += 1

        logger.info("Backfill complete: %d processed, %d failed, %d total", processed, failed, total)
    finally:
        db.close()


if __name__ == "__main__":
    main()
