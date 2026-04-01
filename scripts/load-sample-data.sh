#!/usr/bin/env bash
set -euo pipefail

# Load sample data into DynamoDB tables for testing.
# Requires AWS CLI configured and tables already created.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

AWS_REGION="${AWS_REGION:-us-east-1}"

echo "==> Loading sample data into DynamoDB"
echo "Region: $AWS_REGION"

NOW=$(date +%s)
HOUR_AGO=$((NOW - 3600))
TWO_HOURS_AGO=$((NOW - 7200))
DAY_AGO=$((NOW - 86400))

# Load sample orders
echo "Loading orders..."
aws dynamodb batch-write-item \
  --request-items "{
    \"orders\": [
      {
        \"PutRequest\": {
          \"Item\": {
            \"order_id\": {\"S\": \"ORD-001\"},
            \"customer\": {\"S\": \"Acme Corp\"},
            \"amount\": {\"N\": \"2500.00\"},
            \"status\": {\"S\": \"completed\"},
            \"created_timestamp\": {\"N\": \"$HOUR_AGO\"}
          }
        }
      },
      {
        \"PutRequest\": {
          \"Item\": {
            \"order_id\": {\"S\": \"ORD-002\"},
            \"customer\": {\"S\": \"Beta Inc\"},
            \"amount\": {\"N\": \"1850.50\"},
            \"status\": {\"S\": \"completed\"},
            \"created_timestamp\": {\"N\": \"$TWO_HOURS_AGO\"}
          }
        }
      },
      {
        \"PutRequest\": {
          \"Item\": {
            \"order_id\": {\"S\": \"ORD-003\"},
            \"customer\": {\"S\": \"Gamma Ltd\"},
            \"amount\": {\"N\": \"750.00\"},
            \"status\": {\"S\": \"pending\"},
            \"created_timestamp\": {\"N\": \"$NOW\"}
          }
        }
      }
    ]
  }" \
  --region "$AWS_REGION" || echo "Warning: could not load orders"

# Load sample support tickets
echo "Loading support tickets..."
aws dynamodb batch-write-item \
  --request-items "{
    \"support_tickets\": [
      {
        \"PutRequest\": {
          \"Item\": {
            \"ticket_id\": {\"S\": \"TKT-001\"},
            \"subject\": {\"S\": \"Cannot reset password\"},
            \"status\": {\"S\": \"open\"},
            \"priority\": {\"S\": \"high\"},
            \"created_timestamp\": {\"N\": \"$HOUR_AGO\"}
          }
        }
      },
      {
        \"PutRequest\": {
          \"Item\": {
            \"ticket_id\": {\"S\": \"TKT-002\"},
            \"subject\": {\"S\": \"Feature request: bulk export\"},
            \"status\": {\"S\": \"in-progress\"},
            \"priority\": {\"S\": \"medium\"},
            \"created_timestamp\": {\"N\": \"$TWO_HOURS_AGO\"}
          }
        }
      },
      {
        \"PutRequest\": {
          \"Item\": {
            \"ticket_id\": {\"S\": \"TKT-003\"},
            \"subject\": {\"S\": \"Billing question resolved\"},
            \"status\": {\"S\": \"resolved\"},
            \"priority\": {\"S\": \"low\"},
            \"created_timestamp\": {\"N\": \"$DAY_AGO\"}
          }
        }
      }
    ]
  }" \
  --region "$AWS_REGION" || echo "Warning: could not load tickets"

# Load sample metrics
echo "Loading business metrics..."
aws dynamodb batch-write-item \
  --request-items "{
    \"business_metrics\": [
      {
        \"PutRequest\": {
          \"Item\": {
            \"metric_id\": {\"S\": \"MET-001\"},
            \"timestamp\": {\"N\": \"$NOW\"},
            \"api_calls\": {\"N\": \"5200\"},
            \"database_queries\": {\"N\": \"12500\"},
            \"error_rate\": {\"N\": \"0.0012\"},
            \"uptime\": {\"BOOL\": true}
          }
        }
      },
      {
        \"PutRequest\": {
          \"Item\": {
            \"metric_id\": {\"S\": \"MET-002\"},
            \"timestamp\": {\"N\": \"$HOUR_AGO\"},
            \"api_calls\": {\"N\": \"4800\"},
            \"database_queries\": {\"N\": \"11200\"},
            \"error_rate\": {\"N\": \"0.0008\"},
            \"uptime\": {\"BOOL\": true}
          }
        }
      }
    ]
  }" \
  --region "$AWS_REGION" || echo "Warning: could not load metrics"

echo "==> Sample data loaded successfully"
echo ""
echo "Sample data summary:"
echo "  - 3 orders (2 completed, 1 pending)"
echo "  - 3 support tickets (1 open, 1 in-progress, 1 resolved)"
echo "  - 2 metric data points"
echo ""
echo "You can now trigger the Lambda manually:"
echo "  aws lambda invoke --function-name scheduled-report-generator-dev /tmp/response.json"
