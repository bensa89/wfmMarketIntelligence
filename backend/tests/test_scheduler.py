import pytest
from unittest.mock import MagicMock, patch, call
from app.models.schedule import ScheduleConfig


def _make_config(**kwargs) -> ScheduleConfig:
    defaults = dict(
        crawl_enabled=False,
        crawl_day_of_week=0,
        crawl_time="06:00",
        crawl_timezone="Europe/Berlin",
        digest_after_crawl=True,
        digest_enabled=False,
        digest_day_of_week=1,
        digest_time="08:00",
        email_enabled=False,
        email_recipients=[],
        smtp_host="",
        smtp_port=587,
        smtp_user="",
        smtp_password="",
        smtp_from="",
    )
    defaults.update(kwargs)
    return ScheduleConfig(**defaults)


def test_apply_schedule_adds_crawl_job_when_enabled():
    config = _make_config(crawl_enabled=True, crawl_day_of_week=0, crawl_time="06:00")

    mock_sched = MagicMock()
    mock_sched.running = True
    mock_sched.get_job.return_value = None

    with patch("app.scheduler._scheduler", mock_sched):
        from app.scheduler import apply_schedule
        apply_schedule(config)

    add_calls = mock_sched.add_job.call_args_list
    assert len(add_calls) == 1
    assert add_calls[0][1]["id"] == "job_crawl"


def test_apply_schedule_no_jobs_when_all_disabled():
    config = _make_config(crawl_enabled=False, digest_enabled=False)

    mock_sched = MagicMock()
    mock_sched.running = True
    mock_sched.get_job.return_value = None

    with patch("app.scheduler._scheduler", mock_sched):
        from app.scheduler import apply_schedule
        apply_schedule(config)

    mock_sched.add_job.assert_not_called()


def test_apply_schedule_adds_digest_job_when_independent_schedule():
    config = _make_config(
        crawl_enabled=False,
        digest_after_crawl=False,
        digest_enabled=True,
        digest_day_of_week=2,
        digest_time="08:00",
    )

    mock_sched = MagicMock()
    mock_sched.running = True
    mock_sched.get_job.return_value = None

    with patch("app.scheduler._scheduler", mock_sched):
        from app.scheduler import apply_schedule
        apply_schedule(config)

    add_calls = mock_sched.add_job.call_args_list
    assert len(add_calls) == 1
    assert add_calls[0][1]["id"] == "job_digest"


def test_apply_schedule_removes_existing_jobs_before_readding():
    config = _make_config(crawl_enabled=True)

    mock_sched = MagicMock()
    mock_sched.running = True
    # Simulate existing job
    mock_sched.get_job.return_value = MagicMock()

    with patch("app.scheduler._scheduler", mock_sched):
        from app.scheduler import apply_schedule
        apply_schedule(config)

    remove_calls = [c for c in mock_sched.remove_job.call_args_list]
    assert any(c[0][0] == "job_crawl" for c in remove_calls)


def test_apply_schedule_no_op_when_scheduler_not_running():
    config = _make_config(crawl_enabled=True)

    mock_sched = MagicMock()
    mock_sched.running = False

    with patch("app.scheduler._scheduler", mock_sched):
        from app.scheduler import apply_schedule
        apply_schedule(config)

    mock_sched.add_job.assert_not_called()


def test_apply_schedule_no_op_when_scheduler_is_none():
    config = _make_config(crawl_enabled=True)

    with patch("app.scheduler._scheduler", None):
        from app.scheduler import apply_schedule
        apply_schedule(config)  # must not raise


def test_build_crawl_stats_includes_new_documents_and_analysis_errors():
    from datetime import datetime, timezone
    from app.scheduler import _build_crawl_stats

    crawl_run = MagicMock()
    crawl_run.started_at = datetime(2026, 7, 3, 3, 0, 0, tzinfo=timezone.utc)
    crawl_run.finished_at = datetime(2026, 7, 3, 3, 13, 30, tzinfo=timezone.utc)
    crawl_run.total_sources = 68
    crawl_run.total_new = 76
    crawl_run.total_errors = 3
    crawl_run.total_analysis_errors = 3

    stats = _build_crawl_stats(crawl_run)

    assert stats["new_documents"] == 76
    assert stats["analysis_errors"] == 3
