"""
Tests for the scheduled report generator handler.

Uses mocking to avoid real AWS/Anthropic API calls during CI.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch


from src.handler import (
    ReportContext,
    build_and_send_report,
    generate_insights_with_claude,
    lambda_handler,
    query_business_data,
)


class TestQueryBusinessData:
    def test_query_daily_summary(self):
        """Test querying data for a daily summary report."""
        with patch("src.handler.DynamoDBQueryHelper") as mock_helper_cls:
            mock_helper = MagicMock()
            mock_helper.get_orders_in_window.return_value = [
                {"order_id": "1", "amount": 100},
                {"order_id": "2", "amount": 200},
            ]
            mock_helper.get_tickets_in_window.return_value = [
                {"ticket_id": "t1", "status": "open"},
                {"ticket_id": "t2", "status": "resolved"},
            ]
            mock_helper.get_metrics_in_window.return_value = {
                "uptime_percentage": 99.9,
            }
            mock_helper_cls.return_value = mock_helper

            context = query_business_data("daily_summary")

            assert context.report_type == "daily_summary"
            assert context.time_window_hours == 24
            assert context.orders_count == 2
            assert context.orders_total_amount == 300
            assert context.tickets_count == 2
            assert "open" in context.tickets_by_status
            assert "resolved" in context.tickets_by_status

    def test_query_weekly_digest(self):
        """Test querying data for a weekly digest report."""
        with patch("src.handler.DynamoDBQueryHelper") as mock_helper_cls:
            mock_helper = MagicMock()
            mock_helper.get_orders_in_window.return_value = [
                {"order_id": "1", "amount": 500},
            ]
            mock_helper.get_tickets_in_window.return_value = []
            mock_helper.get_metrics_in_window.return_value = {}
            mock_helper_cls.return_value = mock_helper

            context = query_business_data("weekly_digest")

            assert context.report_type == "weekly_digest"
            assert context.time_window_hours == 168  # 7 days

    def test_query_monthly_review(self):
        """Test querying data for a monthly review report."""
        with patch("src.handler.DynamoDBQueryHelper") as mock_helper_cls:
            mock_helper = MagicMock()
            mock_helper.get_orders_in_window.return_value = []
            mock_helper.get_tickets_in_window.return_value = []
            mock_helper.get_metrics_in_window.return_value = {}
            mock_helper_cls.return_value = mock_helper

            context = query_business_data("monthly_review")

            assert context.report_type == "monthly_review"
            assert context.time_window_hours == 720  # 30 days


class TestGenerateInsights:
    @patch("src.handler.anthropic.Anthropic")
    def test_generate_insights_calls_claude(self, mock_client_cls):
        """Test that Claude is called with correct prompt."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Great insights here!")]
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50
        mock_client.messages.create.return_value = mock_response
        mock_client_cls.return_value = mock_client

        context = ReportContext(
            report_type="daily_summary",
            time_window_hours=24,
            orders_count=5,
            orders_total_amount=1000,
            tickets_count=2,
            tickets_by_status={"open": 1, "resolved": 1},
            metrics={"uptime_percentage": 99.9},
            generated_at="2026-04-01T12:00:00Z",
        )

        insights = generate_insights_with_claude(context)

        assert insights == "Great insights here!"
        mock_client.messages.create.assert_called_once()
        call_args = mock_client.messages.create.call_args
        assert "orders" in call_args.kwargs["messages"][0]["content"].lower()


class TestBuildAndSendReport:
    @patch("src.handler.ses.send_email")
    @patch("src.handler.get_ssm_param")
    def test_build_and_send_report_success(self, mock_get_ssm, mock_ses):
        """Test successful report building and sending."""
        mock_get_ssm.return_value = "sender@example.com"
        mock_ses.return_value = {"MessageId": "msg-123"}

        context = ReportContext(
            report_type="daily_summary",
            time_window_hours=24,
            orders_count=10,
            orders_total_amount=2000,
            tickets_count=3,
            tickets_by_status={"open": 1, "in-progress": 1, "resolved": 1},
            metrics={"uptime_percentage": 99.9},
            generated_at="2026-04-01T12:00:00Z",
        )
        insights = "The business is performing well."
        recipients = ["user@example.com"]

        result = build_and_send_report(context, insights, recipients)

        assert result.sent_successfully is True
        assert result.error is None
        assert result.subject == "Daily Business Summary"
        assert "html_body" in result.__dict__
        mock_ses.assert_called_once()

    @patch("src.handler.get_ssm_param")
    def test_build_report_missing_sender_email(self, mock_get_ssm):
        """Test failure when sender email cannot be retrieved."""
        from botocore.exceptions import ClientError

        mock_get_ssm.side_effect = ClientError(
            {"Error": {"Code": "ParameterNotFound"}}, "GetParameter"
        )

        context = ReportContext(
            report_type="daily_summary",
            time_window_hours=24,
            orders_count=10,
            orders_total_amount=2000,
            tickets_count=3,
            tickets_by_status={"open": 1},
            metrics={},
            generated_at="2026-04-01T12:00:00Z",
        )

        result = build_and_send_report(context, "insights", ["user@example.com"])

        assert result.sent_successfully is False
        assert "sender email" in result.error.lower()

    @patch("src.handler.ses.send_email")
    @patch("src.handler.get_ssm_param")
    def test_build_report_ses_failure(self, mock_get_ssm, mock_ses):
        """Test failure when SES send fails."""
        from botocore.exceptions import ClientError

        mock_get_ssm.return_value = "sender@example.com"
        mock_ses.side_effect = ClientError(
            {"Error": {"Code": "MessageRejected"}}, "SendEmail"
        )

        context = ReportContext(
            report_type="daily_summary",
            time_window_hours=24,
            orders_count=10,
            orders_total_amount=2000,
            tickets_count=3,
            tickets_by_status={},
            metrics={},
            generated_at="2026-04-01T12:00:00Z",
        )

        result = build_and_send_report(context, "insights", ["user@example.com"])

        assert result.sent_successfully is False
        assert "SES" in result.error


class TestLambdaHandler:
    @patch("src.handler.build_and_send_report")
    @patch("src.handler.generate_insights_with_claude")
    @patch("src.handler.query_business_data")
    @patch("src.handler.get_ssm_param")
    def test_lambda_handler_success(
        self,
        mock_get_ssm,
        mock_query,
        mock_insights,
        mock_send,
    ):
        """Test successful lambda handler execution."""
        # Setup mocks
        mock_get_ssm.return_value = json.dumps(["user@example.com"])

        mock_query.return_value = ReportContext(
            report_type="daily_summary",
            time_window_hours=24,
            orders_count=5,
            orders_total_amount=1000,
            tickets_count=2,
            tickets_by_status={"open": 1},
            metrics={"uptime_percentage": 99.9},
            generated_at="2026-04-01T12:00:00Z",
        )

        mock_insights.return_value = "Business is doing great!"

        from src.handler import ReportResult

        mock_send.return_value = ReportResult(
            report_type="daily_summary",
            recipients=["user@example.com"],
            subject="Daily Business Summary",
            html_body="<html>...</html>",
            sent_successfully=True,
            error=None,
            timestamp="2026-04-01T12:00:00Z",
        )

        event = {
            "source": "aws.events",
            "detail-type": "Scheduled Event",
        }

        result = lambda_handler(event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["status"] == "success"
        assert body["report_type"] == "daily_summary"

    @patch("src.handler.get_ssm_param")
    def test_lambda_handler_missing_recipients(self, mock_get_ssm):
        """Test lambda handler when recipients cannot be retrieved."""
        from botocore.exceptions import ClientError

        mock_get_ssm.side_effect = ClientError(
            {"Error": {"Code": "ParameterNotFound"}}, "GetParameter"
        )

        event = {
            "source": "aws.events",
            "detail-type": "Scheduled Event",
        }

        result = lambda_handler(event, None)

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "recipients" in body["error"].lower()

    @patch("src.handler.build_and_send_report")
    @patch("src.handler.generate_insights_with_claude")
    @patch("src.handler.query_business_data")
    @patch("src.handler.get_ssm_param")
    def test_lambda_handler_send_failure(
        self,
        mock_get_ssm,
        mock_query,
        mock_insights,
        mock_send,
    ):
        """Test lambda handler when report send fails."""
        mock_get_ssm.return_value = json.dumps(["user@example.com"])

        mock_query.return_value = ReportContext(
            report_type="daily_summary",
            time_window_hours=24,
            orders_count=5,
            orders_total_amount=1000,
            tickets_count=2,
            tickets_by_status={},
            metrics={},
            generated_at="2026-04-01T12:00:00Z",
        )

        mock_insights.return_value = "Insights here"

        from src.handler import ReportResult

        mock_send.return_value = ReportResult(
            report_type="daily_summary",
            recipients=["user@example.com"],
            subject="Daily Business Summary",
            html_body="<html>...</html>",
            sent_successfully=False,
            error="SES send failed",
            timestamp="2026-04-01T12:00:00Z",
        )

        event = {
            "source": "aws.events",
            "detail-type": "Scheduled Event",
        }

        result = lambda_handler(event, None)

        assert result["statusCode"] == 500
        body = json.loads(result["body"])
        assert body["status"] == "error"

    @patch("src.handler.anthropic.Anthropic")
    @patch("src.handler.query_business_data")
    @patch("src.handler.get_ssm_param")
    def test_lambda_handler_anthropic_error(
        self,
        mock_get_ssm,
        mock_query,
        mock_anthropic_cls,
    ):
        """Test lambda handler handling Anthropic API errors."""
        import anthropic as anthropic_mod

        mock_get_ssm.return_value = json.dumps(["user@example.com"])

        mock_query.return_value = ReportContext(
            report_type="daily_summary",
            time_window_hours=24,
            orders_count=5,
            orders_total_amount=1000,
            tickets_count=2,
            tickets_by_status={},
            metrics={},
            generated_at="2026-04-01T12:00:00Z",
        )

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = anthropic_mod.APIError(
            message="rate limited",
            request=MagicMock(),
            body=None,
        )
        mock_anthropic_cls.return_value = mock_client

        event = {
            "source": "aws.events",
            "detail-type": "Scheduled Event",
        }

        result = lambda_handler(event, None)

        assert result["statusCode"] == 502
        body = json.loads(result["body"])
        assert "AI service" in body["error"]
