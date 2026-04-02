"""Tests for helper utility functions."""

import time
from helpers import fmt, esc, relative_time, time_until, format_duration, job_type, log_name_for_job


class TestFmt:
    """Tests for the fmt() formatter."""

    def test_none(self):
        assert fmt(None) == "—"

    def test_integer(self):
        assert fmt(1234) == "1,234"

    def test_float(self):
        assert fmt(1234567.89) == "1,234,568"

    def test_zero(self):
        assert fmt(0) == "0"

    def test_string(self):
        assert fmt("hello") == "hello"


class TestEsc:
    """Tests for the esc() HTML escaper."""

    def test_none(self):
        assert str(esc(None)) == "—"

    def test_plain(self):
        assert str(esc("hello")) == "hello"

    def test_html(self):
        result = str(esc("<script>alert('xss')</script>"))
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_ampersand(self):
        assert "&amp;" in str(esc("A&B"))


class TestRelativeTime:
    """Tests for relative_time()."""

    def test_none(self):
        assert relative_time(None) == "never"

    def test_zero(self):
        assert relative_time(0) == "never"

    def test_recent(self):
        now_ms = int(time.time() * 1000)
        result = relative_time(now_ms - 300_000)  # 5 min ago
        assert "m ago" in result

    def test_hours(self):
        now_ms = int(time.time() * 1000)
        result = relative_time(now_ms - 7_200_000)  # 2h ago
        assert "h ago" in result

    def test_days(self):
        now_ms = int(time.time() * 1000)
        result = relative_time(now_ms - 259_200_000)  # 3d ago
        assert "d ago" in result


class TestTimeUntil:
    """Tests for time_until()."""

    def test_none(self):
        assert time_until(None) == "—"

    def test_future(self):
        future_ms = int(time.time() * 1000) + 3_600_000
        result = time_until(future_ms)
        assert result.startswith("in ")

    def test_overdue(self):
        past_ms = int(time.time() * 1000) - 3_600_000
        assert time_until(past_ms) == "overdue"


class TestFormatDuration:
    """Tests for format_duration()."""

    def test_none(self):
        assert format_duration(None) == "—"

    def test_zero(self):
        assert format_duration(0) == "—"

    def test_seconds(self):
        assert format_duration(45000) == "45s"

    def test_minutes(self):
        assert format_duration(192000) == "3.2m"

    def test_hours(self):
        assert format_duration(5400000) == "1.5h"


class TestJobType:
    """Tests for job_type()."""

    def test_enrich(self):
        assert job_type("IGD Batch Enrich (morning)") == "enrich"

    def test_discover(self):
        assert job_type("IGD Discover New Games") == "discover"

    def test_gather(self):
        assert job_type("Gather games") == "discover"

    def test_snapshot(self):
        assert job_type("Daily Snapshot + Score") == "snapshot"

    def test_export(self):
        assert job_type("Export + Deploy Site") == "export"

    def test_article(self):
        assert job_type("Morning Article") == "article"

    def test_trend(self):
        assert job_type("Weekly Trend Report") == "article"

    def test_other(self):
        assert job_type("Random Job") == "other"


class TestLogNameForJob:
    """Tests for log_name_for_job()."""

    def test_enrich(self):
        assert log_name_for_job("Batch Enrich") == "batch_enrich"

    def test_discover(self):
        assert log_name_for_job("Discover Games") == "gather"

    def test_snapshot(self):
        assert log_name_for_job("Snapshot") == "snapshot"

    def test_export(self):
        assert log_name_for_job("Export") == "export"

    def test_unknown(self):
        assert log_name_for_job("Random") == "unknown"
