"""
Tests for report template rendering.
"""

from __future__ import annotations

import pytest

from src.report_templates import (
    render_daily_summary,
    render_monthly_review,
    render_report_html,
    render_weekly_digest,
)


class TestDailySummaryTemplate:
    def test_render_daily_summary(self):
        """Test rendering daily summary template."""
        context = {
            "orders_count": 15,
            "orders_total_amount": 3500.00,
            "tickets_count": 8,
            "tickets_by_status": {"open": 3, "in-progress": 2, "resolved": 3},
            "metrics": {
                "uptime_percentage": 99.9,
                "error_rate": 0.001,
                "customer_satisfaction": 4.7,
            },
            "insights": "Business is performing well.\nOrders are up 20% from yesterday.",
            "timezone": "America/New_York",
            "generated_at": "2026-04-01T12:00:00Z",
        }

        html = render_daily_summary(context)

        assert "Daily Business Summary" in html
        assert "15" in html  # orders
        assert "3500" in html  # revenue
        assert "8" in html  # tickets
        assert "99.9" in html  # uptime
        assert "Business is performing well" in html

    def test_render_daily_summary_with_empty_tickets(self):
        """Test rendering when there are no tickets."""
        context = {
            "orders_count": 5,
            "orders_total_amount": 1000.00,
            "tickets_count": 0,
            "tickets_by_status": {},
            "metrics": {"uptime_percentage": 100.0},
            "insights": "All systems normal.",
            "timezone": "UTC",
            "generated_at": "2026-04-01T12:00:00Z",
        }

        html = render_daily_summary(context)

        assert "Daily Business Summary" in html
        assert "5" in html
        assert "1000" in html


class TestWeeklyDigestTemplate:
    def test_render_weekly_digest(self):
        """Test rendering weekly digest template."""
        context = {
            "orders_count": 100,
            "orders_total_amount": 25000.00,
            "tickets_count": 42,
            "tickets_by_status": {"open": 5, "in-progress": 10, "resolved": 27},
            "metrics": {
                "uptime_percentage": 99.95,
                "error_rate": 0.0005,
                "customer_satisfaction": 4.8,
                "api_calls": 50000,
            },
            "insights": "Weekly trends show strong growth.",
            "timezone": "America/Los_Angeles",
            "generated_at": "2026-04-01T12:00:00Z",
        }

        html = render_weekly_digest(context)

        assert "Weekly Business Digest" in html
        assert "100" in html  # orders
        assert "25000" in html  # revenue
        assert "250" in html  # avg order value
        assert "42" in html  # tickets
        assert "99.95" in html  # uptime
        assert "Weekly trends" in html


class TestMonthlyReviewTemplate:
    def test_render_monthly_review(self):
        """Test rendering monthly review template."""
        context = {
            "orders_count": 450,
            "orders_total_amount": 112500.00,
            "tickets_count": 185,
            "tickets_by_status": {
                "open": 8,
                "in-progress": 15,
                "resolved": 162,
            },
            "metrics": {
                "uptime_percentage": 99.98,
                "error_rate": 0.0002,
                "customer_satisfaction": 4.85,
                "api_calls": 500000,
                "database_queries": 1000000,
            },
            "insights": "Strong month with excellent system stability.",
            "timezone": "Europe/London",
            "generated_at": "2026-04-01T12:00:00Z",
        }

        html = render_monthly_review(context)

        assert "Monthly Business Review" in html
        assert "450" in html  # orders
        assert "112500" in html  # revenue
        assert "185" in html  # tickets
        assert "99.98" in html  # uptime
        assert "500000" in html  # API calls
        assert "1000000" in html  # database queries
        assert "Strong month" in html


class TestTemplateRegistry:
    def test_render_report_html_daily(self):
        """Test render_report_html for daily summary."""
        context = {
            "orders_count": 10,
            "orders_total_amount": 2000.00,
            "tickets_count": 5,
            "tickets_by_status": {"open": 2, "resolved": 3},
            "metrics": {"uptime_percentage": 99.9},
            "insights": "Good day.",
            "timezone": "UTC",
            "generated_at": "2026-04-01T12:00:00Z",
        }

        html = render_report_html("daily_summary", context)

        assert "Daily Business Summary" in html
        assert "10" in html

    def test_render_report_html_weekly(self):
        """Test render_report_html for weekly digest."""
        context = {
            "orders_count": 70,
            "orders_total_amount": 14000.00,
            "tickets_count": 35,
            "tickets_by_status": {"open": 5, "resolved": 30},
            "metrics": {"uptime_percentage": 99.95},
            "insights": "Great week.",
            "timezone": "UTC",
            "generated_at": "2026-04-01T12:00:00Z",
        }

        html = render_report_html("weekly_digest", context)

        assert "Weekly Business Digest" in html
        assert "70" in html

    def test_render_report_html_monthly(self):
        """Test render_report_html for monthly review."""
        context = {
            "orders_count": 300,
            "orders_total_amount": 60000.00,
            "tickets_count": 120,
            "tickets_by_status": {"open": 10, "resolved": 110},
            "metrics": {"uptime_percentage": 99.98},
            "insights": "Excellent month.",
            "timezone": "UTC",
            "generated_at": "2026-04-01T12:00:00Z",
        }

        html = render_report_html("monthly_review", context)

        assert "Monthly Business Review" in html
        assert "300" in html

    def test_render_report_html_invalid_template(self):
        """Test render_report_html with invalid template name."""
        context = {}

        with pytest.raises(ValueError, match="Unknown template"):
            render_report_html("invalid_template", context)

    def test_html_contains_proper_structure(self):
        """Test that rendered HTML contains proper structure."""
        context = {
            "orders_count": 5,
            "orders_total_amount": 1000.00,
            "tickets_count": 2,
            "tickets_by_status": {"open": 1},
            "metrics": {"uptime_percentage": 99.9},
            "insights": "Insight text.",
            "timezone": "UTC",
            "generated_at": "2026-04-01T12:00:00Z",
        }

        html = render_daily_summary(context)

        # Check structure
        assert html.startswith("<!DOCTYPE html>")
        assert "<html>" in html
        assert "</html>" in html
        assert "<head>" in html
        assert "<body>" in html
        assert "<style>" in html
        assert "text/html" not in html or "charset" in html


class TestAveragingLogic:
    def test_monthly_review_average_calculations(self):
        """Test that monthly review correctly calculates daily averages."""
        context = {
            "orders_count": 300,
            "orders_total_amount": 60000.00,
            "tickets_count": 120,
            "tickets_by_status": {"open": 10, "resolved": 110},
            "metrics": {"uptime_percentage": 99.98},
            "insights": "Monthly review.",
            "timezone": "UTC",
            "generated_at": "2026-04-01T12:00:00Z",
        }

        html = render_monthly_review(context)

        # 300 / 30 = 10 orders per day
        assert "10.0" in html or "10" in html
        # 60000 / 30 = 2000 per day
        assert "2000" in html or "2,000" in html
