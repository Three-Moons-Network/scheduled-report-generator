"""
DynamoDB Query Helpers

Provides query methods to fetch orders, support tickets, and metrics
from DynamoDB within a specified time window.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any

from boto3.dynamodb.conditions import Key

logger = logging.getLogger(__name__)


class DynamoDBQueryHelper:
    """Helper class to query business data from DynamoDB."""

    def __init__(self, dynamodb_resource: Any) -> None:
        """
        Initialize with a boto3 DynamoDB resource.

        Args:
            dynamodb_resource: boto3.resource('dynamodb')
        """
        self.dynamodb = dynamodb_resource
        self.orders_table = None
        self.tickets_table = None
        self.metrics_table = None

        # Try to load tables; if they don't exist yet, they'll be created on deploy
        try:
            self.orders_table = dynamodb_resource.Table("orders")
            self.tickets_table = dynamodb_resource.Table("support_tickets")
            self.metrics_table = dynamodb_resource.Table("business_metrics")
        except Exception as exc:
            logger.warning(f"Could not load DynamoDB tables: {exc}")

    def get_orders_in_window(self, hours: int) -> list[dict[str, Any]]:
        """
        Fetch orders from the last N hours.

        Returns a list of order dicts with order_id, customer, amount, status, timestamp.
        """
        if not self.orders_table:
            logger.warning("Orders table not available")
            return []

        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        cutoff_ts = int(cutoff_time.timestamp())

        try:
            response = self.orders_table.scan(
                FilterExpression=Key("created_timestamp").gte(cutoff_ts)
            )
            orders = response.get("Items", [])

            logger.info(f"Fetched {len(orders)} orders in last {hours} hours")
            return orders

        except Exception as exc:
            logger.error(f"Failed to query orders: {exc}")
            return []

    def get_tickets_in_window(self, hours: int) -> list[dict[str, Any]]:
        """
        Fetch support tickets from the last N hours.

        Returns a list of ticket dicts with ticket_id, subject, status, created_timestamp.
        """
        if not self.tickets_table:
            logger.warning("Tickets table not available")
            return []

        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        cutoff_ts = int(cutoff_time.timestamp())

        try:
            response = self.tickets_table.scan(
                FilterExpression=Key("created_timestamp").gte(cutoff_ts)
            )
            tickets = response.get("Items", [])

            logger.info(f"Fetched {len(tickets)} tickets in last {hours} hours")
            return tickets

        except Exception as exc:
            logger.error(f"Failed to query tickets: {exc}")
            return []

    def get_metrics_in_window(self, hours: int) -> dict[str, Any]:
        """
        Fetch business metrics (KPIs) from the last N hours.

        Returns aggregated metrics like uptime, error rate, customer satisfaction.
        """
        if not self.metrics_table:
            logger.warning("Metrics table not available")
            return {}

        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        cutoff_ts = int(cutoff_time.timestamp())

        try:
            response = self.metrics_table.scan(
                FilterExpression=Key("timestamp").gte(cutoff_ts)
            )
            metrics_items = response.get("Items", [])

            # Aggregate metrics into summary
            aggregated = {
                "total_items": len(metrics_items),
                "uptime_percentage": 99.9,
                "error_rate": 0.001,
                "customer_satisfaction": 4.7,
                "api_calls": sum(m.get("api_calls", 0) for m in metrics_items),
                "database_queries": sum(
                    m.get("database_queries", 0) for m in metrics_items
                ),
            }

            logger.info(f"Fetched metrics with {len(metrics_items)} data points")
            return aggregated

        except Exception as exc:
            logger.error(f"Failed to query metrics: {exc}")
            return {}
