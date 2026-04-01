"""
Scheduled Report Generator — Lambda Handler

On a configured schedule, queries DynamoDB for business data (orders, support
tickets, metrics), calls Claude to generate insights, and sends formatted HTML
reports via SES email.

Supported report types: daily_summary, weekly_digest, monthly_review
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any

import anthropic
import boto3
from botocore.exceptions import BotoCoreError, ClientError

from src.dynamodb_queries import DynamoDBQueryHelper
from src.report_templates import REPORT_TEMPLATES, render_report_html

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "2048"))
REPORT_TYPE = os.environ.get("REPORT_TYPE", "daily_summary")
TIMEZONE = os.environ.get("TIMEZONE", "America/New_York")

# AWS Service clients
dynamodb = boto3.resource("dynamodb")
ssm = boto3.client("ssm")
ses = boto3.client("ses")

# Cache SSM parameters
_ssm_cache: dict[str, Any] = {}


def get_ssm_param(param_name: str, decrypt: bool = True) -> str:
    """Fetch SSM parameter with caching."""
    if param_name in _ssm_cache:
        return _ssm_cache[param_name]

    try:
        response = ssm.get_parameter(Name=param_name, WithDecryption=decrypt)
        value = response["Parameter"]["Value"]
        _ssm_cache[param_name] = value
        return value
    except ClientError as exc:
        logger.error(f"Failed to fetch SSM parameter {param_name}: {exc}")
        raise


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ReportContext:
    """Context data for report generation."""

    report_type: str
    time_window_hours: int
    orders_count: int
    orders_total_amount: float
    tickets_count: int
    tickets_by_status: dict[str, int]
    metrics: dict[str, Any]
    generated_at: str


@dataclass
class ReportResult:
    """Result of report generation and delivery."""

    report_type: str
    recipients: list[str]
    subject: str
    html_body: str
    sent_successfully: bool
    error: str | None
    timestamp: str


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def query_business_data(report_type: str) -> ReportContext:
    """
    Query DynamoDB for business data based on report type.

    Returns aggregated metrics for the last N hours depending on report type.
    """
    # Determine time window
    if report_type == "daily_summary":
        hours = 24
    elif report_type == "weekly_digest":
        hours = 7 * 24
    elif report_type == "monthly_review":
        hours = 30 * 24
    else:
        hours = 24

    # Initialize query helper
    query_helper = DynamoDBQueryHelper(dynamodb)

    # Query orders
    orders = query_helper.get_orders_in_window(hours)
    orders_count = len(orders)
    orders_total_amount = sum(o.get("amount", 0) for o in orders)

    # Query support tickets
    tickets = query_helper.get_tickets_in_window(hours)
    tickets_count = len(tickets)
    tickets_by_status = {}
    for ticket in tickets:
        status = ticket.get("status", "unknown")
        tickets_by_status[status] = tickets_by_status.get(status, 0) + 1

    # Query metrics (business KPIs)
    metrics = query_helper.get_metrics_in_window(hours)

    logger.info(
        "Queried business data",
        extra={
            "report_type": report_type,
            "hours": hours,
            "orders": orders_count,
            "tickets": tickets_count,
            "metrics_points": len(metrics),
        },
    )

    return ReportContext(
        report_type=report_type,
        time_window_hours=hours,
        orders_count=orders_count,
        orders_total_amount=orders_total_amount,
        tickets_count=tickets_count,
        tickets_by_status=tickets_by_status,
        metrics=metrics,
        generated_at=datetime.utcnow().isoformat() + "Z",
    )


def generate_insights_with_claude(context: ReportContext) -> str:
    """
    Call Claude to generate natural-language insights from business data.

    Returns the generated insight text.
    """
    client = anthropic.Anthropic()

    system_prompt = f"""You are a business intelligence analyst. Generate a concise,
actionable {context.report_type.replace('_', ' ')} report based on the provided business data.

Focus on:
- Key trends and changes from the previous period
- Areas of concern or high activity
- Recommendations for improvement
- Notable metrics and their significance

Keep the tone professional but accessible to business stakeholders.
Use specific numbers and comparisons. Format insights as a series of clear, short paragraphs."""

    user_message = f"""Please analyze this business data and generate insights:

Orders (last {context.time_window_hours} hours):
- Total orders: {context.orders_count}
- Total revenue: ${context.orders_total_amount:,.2f}

Support Tickets (last {context.time_window_hours} hours):
- Total tickets: {context.tickets_count}
- By status: {json.dumps(context.tickets_by_status)}

Business Metrics:
{json.dumps(context.metrics, indent=2)}

Generate actionable insights for decision-makers."""

    logger.info(
        "Calling Claude for insights",
        extra={"model": ANTHROPIC_MODEL, "max_tokens": MAX_TOKENS},
    )

    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=MAX_TOKENS,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    insights = response.content[0].text

    logger.info(
        "Generated insights",
        extra={
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        },
    )

    return insights


def build_and_send_report(
    context: ReportContext, insights: str, recipients: list[str]
) -> ReportResult:
    """
    Build HTML report and send via SES.

    Returns success/failure status and any error messages.
    """
    # Get sender email from SSM
    try:
        sender_email = get_ssm_param("/scheduled-report-generator/ses-sender-email")
    except ClientError as exc:
        logger.error(f"Failed to get SES sender email: {exc}")
        return ReportResult(
            report_type=context.report_type,
            recipients=recipients,
            subject="",
            html_body="",
            sent_successfully=False,
            error="Failed to retrieve sender email configuration",
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

    # Render HTML report from template
    try:
        html_body = render_report_html(
            template_name=context.report_type,
            context={
                "orders_count": context.orders_count,
                "orders_total_amount": context.orders_total_amount,
                "tickets_count": context.tickets_count,
                "tickets_by_status": context.tickets_by_status,
                "metrics": context.metrics,
                "insights": insights,
                "timezone": TIMEZONE,
                "generated_at": context.generated_at,
            },
        )
    except ValueError as exc:
        logger.error(f"Failed to render report template: {exc}")
        return ReportResult(
            report_type=context.report_type,
            recipients=recipients,
            subject="",
            html_body="",
            sent_successfully=False,
            error=f"Template rendering failed: {exc}",
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

    # Build email subject
    subject_map = {
        "daily_summary": "Daily Business Summary",
        "weekly_digest": "Weekly Business Digest",
        "monthly_review": "Monthly Business Review",
    }
    subject = subject_map.get(context.report_type, "Business Report")

    # Send via SES
    try:
        response = ses.send_email(
            Source=sender_email,
            Destination={"ToAddresses": recipients},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Html": {"Data": html_body, "Charset": "UTF-8"}},
            },
        )

        logger.info(
            "Report sent successfully",
            extra={
                "report_type": context.report_type,
                "recipients": len(recipients),
                "message_id": response["MessageId"],
            },
        )

        return ReportResult(
            report_type=context.report_type,
            recipients=recipients,
            subject=subject,
            html_body=html_body,
            sent_successfully=True,
            error=None,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

    except ClientError as exc:
        logger.error(f"SES send failed: {exc}")
        return ReportResult(
            report_type=context.report_type,
            recipients=recipients,
            subject=subject,
            html_body=html_body,
            sent_successfully=False,
            error=f"SES send failed: {exc}",
            timestamp=datetime.utcnow().isoformat() + "Z",
        )


# ---------------------------------------------------------------------------
# Lambda entry point
# ---------------------------------------------------------------------------


def lambda_handler(event: dict, context: Any) -> dict:
    """
    AWS Lambda handler triggered by EventBridge scheduler.

    Queries business data from DynamoDB, generates insights with Claude,
    and sends formatted HTML reports via SES.

    Returns:
      - statusCode 200 with report result on success
      - statusCode 400 on configuration errors
      - statusCode 500 on unexpected failures
    """
    logger.info(
        "Report generation started",
        extra={
            "report_type": REPORT_TYPE,
            "event_source": event.get("source"),
        },
    )

    try:
        # Fetch configuration from SSM
        try:
            recipients_json = get_ssm_param(
                "/scheduled-report-generator/report-recipients"
            )
            recipients = json.loads(recipients_json)
        except (ClientError, json.JSONDecodeError) as exc:
            logger.error(f"Failed to get report recipients: {exc}")
            raise ValueError("Invalid or missing report recipients configuration")

        # Query business data
        report_context = query_business_data(REPORT_TYPE)

        # Generate insights with Claude
        insights = generate_insights_with_claude(report_context)

        # Build and send report
        result = build_and_send_report(report_context, insights, recipients)

        if result.sent_successfully:
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(
                    {
                        "status": "success",
                        "report_type": result.report_type,
                        "recipients": result.recipients,
                        "subject": result.subject,
                        "timestamp": result.timestamp,
                    }
                ),
            }
        else:
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(
                    {
                        "status": "error",
                        "error": result.error,
                        "timestamp": result.timestamp,
                    }
                ),
            }

    except ValueError as exc:
        logger.warning(f"Configuration error: {exc}")
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(exc)}),
        }

    except anthropic.APIError as exc:
        logger.error(f"Anthropic API error: {exc}")
        return {
            "statusCode": 502,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {"error": "AI service temporarily unavailable. Please retry."}
            ),
        }

    except Exception as exc:
        logger.exception(f"Unexpected error: {exc}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Internal server error"}),
        }
