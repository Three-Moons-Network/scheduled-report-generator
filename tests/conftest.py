"""
Shared test fixtures for scheduled report generator tests.
"""

# Set AWS env vars at module level BEFORE any imports of src code
import os

os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_SECURITY_TOKEN", "testing")
os.environ.setdefault("AWS_SESSION_TOKEN", "testing")

import json
from unittest.mock import MagicMock, patch

import boto3
import pytest
from moto import mock_aws


@pytest.fixture
def aws_credentials(monkeypatch):
    """Set fake AWS credentials for testing."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")


@pytest.fixture
def mock_dynamodb_tables(aws_credentials):
    """Create mock DynamoDB tables for testing."""
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

        # Create orders table
        orders_table = dynamodb.create_table(
            TableName="orders",
            KeySchema=[{"AttributeName": "order_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "order_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        # Create support_tickets table
        tickets_table = dynamodb.create_table(
            TableName="support_tickets",
            KeySchema=[{"AttributeName": "ticket_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "ticket_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        # Create business_metrics table
        metrics_table = dynamodb.create_table(
            TableName="business_metrics",
            KeySchema=[{"AttributeName": "metric_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "metric_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        yield {
            "orders": orders_table,
            "tickets": tickets_table,
            "metrics": metrics_table,
            "dynamodb": dynamodb,
        }


@pytest.fixture
def mock_ssm_params(aws_credentials):
    """Create mock SSM parameters for testing."""
    with mock_aws():
        ssm = boto3.client("ssm", region_name="us-east-1")

        # Create test parameters
        ssm.put_parameter(
            Name="/scheduled-report-generator/ses-sender-email",
            Value="reports@example.com",
            Type="String",
        )
        ssm.put_parameter(
            Name="/scheduled-report-generator/report-recipients",
            Value=json.dumps(["user1@example.com", "user2@example.com"]),
            Type="String",
        )
        ssm.put_parameter(
            Name="/scheduled-report-generator/report-type",
            Value="daily_summary",
            Type="String",
        )

        yield ssm


@pytest.fixture
def sample_order_data():
    """Sample order records for testing."""
    import time

    now = int(time.time())
    return [
        {
            "order_id": "ORD-001",
            "customer": "Alice Johnson",
            "amount": 150.00,
            "status": "completed",
            "created_timestamp": now - 3600,
        },
        {
            "order_id": "ORD-002",
            "customer": "Bob Smith",
            "amount": 275.50,
            "status": "completed",
            "created_timestamp": now - 7200,
        },
        {
            "order_id": "ORD-003",
            "customer": "Carol White",
            "amount": 89.99,
            "status": "pending",
            "created_timestamp": now - 1800,
        },
    ]


@pytest.fixture
def sample_ticket_data():
    """Sample support ticket records for testing."""
    import time

    now = int(time.time())
    return [
        {
            "ticket_id": "TKT-001",
            "subject": "Cannot login",
            "status": "open",
            "created_timestamp": now - 7200,
        },
        {
            "ticket_id": "TKT-002",
            "subject": "Billing question",
            "status": "in-progress",
            "created_timestamp": now - 3600,
        },
        {
            "ticket_id": "TKT-003",
            "subject": "Feature request",
            "status": "resolved",
            "created_timestamp": now - 86400,
        },
    ]


@pytest.fixture
def sample_metrics_data():
    """Sample metrics records for testing."""
    import time

    now = int(time.time())
    return [
        {
            "metric_id": "MET-001",
            "timestamp": now - 3600,
            "api_calls": 2500,
            "database_queries": 5000,
            "uptime": True,
        },
        {
            "metric_id": "MET-002",
            "timestamp": now - 1800,
            "api_calls": 1800,
            "database_queries": 3200,
            "uptime": True,
        },
    ]


def _mock_anthropic_response(text: str = "Sample insight") -> MagicMock:
    """Build a mock that mimics anthropic.messages.create() response."""
    response = MagicMock()
    response.content = [MagicMock(text=text)]
    response.model = "claude-sonnet-4-20250514"
    response.usage.input_tokens = 100
    response.usage.output_tokens = 50
    return response


@pytest.fixture
def mock_anthropic():
    """Mock the Anthropic client."""
    with patch("src.handler.anthropic.Anthropic") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_anthropic_response(
            "This is a sample AI-generated insight."
        )
        mock_client_cls.return_value = mock_client
        yield mock_client_cls
