# Scheduled Report Generator

Production-ready scheduled report generator on AWS. EventBridge triggers a Lambda on a configurable schedule (daily/weekly), which queries business data from DynamoDB, generates natural-language insights using Claude, formats an HTML report, and delivers via SES email.

Built as a reference implementation by [Three Moons Network](https://threemoonsnetwork.net) — an AI consulting practice helping small businesses automate with production-grade systems.

## Architecture

```
                    ┌─────────────────────────────────────────────────────┐
                    │                     AWS Cloud                       │
                    │                                                     │
  EventBridge       │                    Lambda Function                 │
  Scheduler ──────▶ │  ┌──────────────────────────────────────────────┐  │
  (daily/weekly)    │  │ 1. Query DynamoDB (orders, metrics, tickets) │  │
                    │  │ 2. Call Claude to generate insights          │  │
                    │  │ 3. Format HTML report with templates         │  │
                    │  │ 4. Send via SES                              │  │
                    │  └──────────────────────────────────────────────┘  │
                    │              │              │                      │
                    │              ▼              ▼                      │
                    │        DynamoDB         SES (Email)                │
                    │        (data)           (delivery)                 │
                    │              │                      │              │
                    │              ▼                      ▼              │
                    │        CloudWatch Log           Email Inbox        │
                    │        Group + Alarms           (recipients)       │
                    │                                                     │
                    │        SSM Parameter Store                         │
                    │        (config, API key)                           │
                    └─────────────────────────────────────────────────────┘
```

## What It Does

On a configured schedule, the Lambda:

1. **Queries DynamoDB** for business data (orders, support tickets, metrics) within a time window
2. **Calls Claude** with configurable report templates to generate natural-language summary, trends, and insights
3. **Formats HTML** from a template with embedded insights and metrics
4. **Sends via SES** to configured recipients with rich formatting and actionable summaries

### Supported Report Types

| Template | Window | Use Case |
|----------|--------|----------|
| daily_summary | Last 24h | Overnight summary of key metrics and alerts |
| weekly_digest | Last 7d | Aggregated trends, top issues, performance review |
| monthly_review | Last 30d | Strategic review, growth metrics, problem areas |

## Quick Start

### Prerequisites

- AWS account with CLI configured
- Terraform >= 1.5
- Python 3.11+
- Anthropic API key ([console.anthropic.com](https://console.anthropic.com))
- Verified SES sender identity (email address or domain)

### 1. Clone and configure

```bash
git clone git@github.com:Three-Moons-Network/scheduled-report-generator.git
cd scheduled-report-generator
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
# Edit terraform.tfvars with your API key, email, and schedule
```

### 2. Build Lambda package

```bash
./scripts/deploy.sh
```

### 3. Load sample data (optional)

```bash
./scripts/load-sample-data.sh
```

This populates the DynamoDB tables with realistic sample orders, support tickets, and metrics.

### 4. Deploy

```bash
cd terraform
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

Terraform outputs the Lambda function name and report schedule.

### 5. Tear down

```bash
terraform destroy
```

## Project Structure

```
├── src/
│   ├── handler.py               # Main Lambda handler
│   ├── report_templates.py       # HTML templates for daily/weekly/monthly
│   └── dynamodb_queries.py       # DynamoDB query helpers
├── tests/
│   ├── test_handler.py          # Handler tests with moto (AWS mock)
│   ├── test_templates.py        # Template rendering tests
│   └── conftest.py              # Shared fixtures
├── terraform/
│   ├── main.tf                  # EventBridge, Lambda, DynamoDB, SES, IAM
│   ├── variables.tf             # Input variables
│   ├── outputs.tf               # Outputs
│   ├── backend.tf               # Remote state config
│   └── terraform.tfvars.example # Example configuration
├── scripts/
│   ├── deploy.sh                # Build Lambda zip package
│   └── load-sample-data.sh      # Populate DynamoDB with test data
├── .github/workflows/
│   └── ci.yml                   # Test, lint, TF validate, package
├── requirements.txt             # Runtime: anthropic, boto3
└── requirements-dev.txt         # Dev: pytest, moto, ruff
```

## Infrastructure Details

| Resource | Purpose |
|----------|---------|
| EventBridge Rule | Cron-based scheduler (configurable: daily/weekly) |
| Lambda (Python 3.11) | Report generation, DynamoDB queries, SES send |
| DynamoDB Tables | orders, support_tickets, business_metrics (sample data) |
| SES Identity | Email sender (domain or email verified in AWS) |
| SSM Parameter Store | Config: recipients, schedule, Claude API key, templates |
| CloudWatch Log Groups | Lambda logs, DynamoDB stream logs |
| CloudWatch Alarms | Lambda errors, DynamoDB throttling |
| IAM Role + Policy | Least-privilege: DynamoDB read, SES send, SSM read, CloudWatch logs |

All resources tagged with Project, Environment, ManagedBy, and Owner for governance.

## Configuration

Edit `terraform.tfvars` to customize:

```hcl
aws_region            = "us-east-1"
project_name          = "scheduled-report-generator"
environment           = "dev"

# Email configuration
ses_sender_email      = "reports@yourcompany.com"
report_recipients     = ["stakeholder@example.com", "ops@example.com"]

# Schedule: use cron expression (UTC)
# "0 9 * * *"     = Every day at 9:00 AM UTC
# "0 9 * * 1"     = Every Monday at 9:00 AM UTC
# "0 8 * * MON-FRI" = Weekdays at 8:00 AM UTC
report_schedule_cron = "0 9 * * *"

# Report type: daily_summary, weekly_digest, or monthly_review
report_type          = "daily_summary"

# TimeZone for display in reports (IANA timezone)
report_timezone      = "America/New_York"

anthropic_api_key    = "sk-ant-..."
anthropic_model      = "claude-sonnet-4-20250514"
```

## Customization

**Add a custom report template:**

1. Create a new function in `src/report_templates.py` with your HTML template
2. Update `REPORT_TEMPLATES` dict to include the new template name
3. Update `SSM` configuration to reference it
4. Add tests in `tests/test_templates.py`

**Change the data query:**

Modify `src/dynamodb_queries.py` to pull different metrics or add custom aggregations.

**Switch models:**

Set `anthropic_model` in tfvars or pass at plan time:

```bash
terraform plan -var="anthropic_model=claude-opus-4-20250514" -out=tfplan
```

## Cost Estimate

For daily reports to a small team:

| Component | Estimated Monthly Cost |
|-----------|----------------------|
| Lambda | ~$0 (free tier: 1M requests, 400K GB-seconds) |
| EventBridge | ~$0.50 (1,440 rules * 12 cents per rule-evaluation) |
| DynamoDB | ~$1-5 (on-demand or provisioned) |
| SES | ~$0.10 (daily send to 3 recipients) |
| CloudWatch | ~$0.50 (log storage) |
| Anthropic API | Usage-based (~$3/M input tokens, ~$15/M output tokens for Sonnet) |

**Total infrastructure: ~$2-6/month.** Your main cost is Anthropic API usage.

## Local Development

```bash
# Set up
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

# Run tests
pytest tests/ -v

# Lint
ruff check src/ tests/
ruff format src/ tests/

# Test handler locally with sample event
export ANTHROPIC_API_KEY="sk-ant-..."
python -c "
from src.handler import lambda_handler
import json
event = {
    'source': 'aws.events',
    'detail-type': 'Scheduled Event'
}
result = lambda_handler(event, None)
print(json.dumps(json.loads(result['body']), indent=2))
"
```

## Monitoring

CloudWatch Dashboard shows:

- Lambda invocation count, errors, duration p99
- DynamoDB read/write throttling
- SES send success/bounce/complaint metrics
- Report generation latency

Access via AWS Console or CLI:

```bash
aws cloudwatch get-dashboard --dashboard-name scheduled-report-generator-dev
```

## License

MIT

## Author

Charles Harvey ([linuxlsr](https://github.com/linuxlsr)) — [Three Moons Network LLC](https://threemoonsnetwork.net)
