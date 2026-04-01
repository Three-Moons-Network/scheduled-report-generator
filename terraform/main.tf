###############################################################################
# Scheduled Report Generator — Infrastructure
#
# Deploys:
#   - EventBridge scheduled rule (daily/weekly/monthly)
#   - Lambda function for report generation
#   - DynamoDB tables for business data
#   - SES for email delivery
#   - SSM Parameter Store for configuration
#   - IAM roles and policies
#   - CloudWatch logs and alarms
###############################################################################

terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
      Owner       = "Three-Moons-Network"
    }
  }
}

locals {
  prefix = "${var.project_name}-${var.environment}"
}

# ---------------------------------------------------------------------------
# SSM Parameter Store — Configuration
# ---------------------------------------------------------------------------

resource "aws_ssm_parameter" "anthropic_api_key" {
  name        = "/${var.project_name}/anthropic-api-key"
  description = "Anthropic API key for Claude inference"
  type        = "SecureString"
  value       = var.anthropic_api_key

  tags = {
    Name = "${local.prefix}-anthropic-api-key"
  }
}

resource "aws_ssm_parameter" "ses_sender_email" {
  name        = "/${var.project_name}/ses-sender-email"
  description = "SES sender email address"
  type        = "String"
  value       = var.ses_sender_email

  tags = {
    Name = "${local.prefix}-ses-sender-email"
  }
}

resource "aws_ssm_parameter" "report_recipients" {
  name        = "/${var.project_name}/report-recipients"
  description = "JSON list of email recipients for reports"
  type        = "String"
  value       = jsonencode(var.report_recipients)

  tags = {
    Name = "${local.prefix}-report-recipients"
  }
}

# ---------------------------------------------------------------------------
# CloudWatch Log Group
# ---------------------------------------------------------------------------

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${local.prefix}"
  retention_in_days = var.log_retention_days

  tags = {
    Name = "${local.prefix}-logs"
  }
}

# ---------------------------------------------------------------------------
# IAM Role and Policies
# ---------------------------------------------------------------------------

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda" {
  name               = "${local.prefix}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json

  tags = {
    Name = "${local.prefix}-lambda-role"
  }
}

data "aws_iam_policy_document" "lambda_permissions" {
  # CloudWatch Logs
  statement {
    sid    = "AllowCloudWatchLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["${aws_cloudwatch_log_group.lambda.arn}:*"]
  }

  # DynamoDB read access
  statement {
    sid    = "AllowDynamoDBRead"
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:Query",
      "dynamodb:Scan",
    ]
    resources = [
      aws_dynamodb_table.orders.arn,
      aws_dynamodb_table.support_tickets.arn,
      aws_dynamodb_table.business_metrics.arn,
    ]
  }

  # SSM Parameter Store read
  statement {
    sid    = "AllowSSMRead"
    effect = "Allow"
    actions = [
      "ssm:GetParameter",
    ]
    resources = [
      aws_ssm_parameter.anthropic_api_key.arn,
      aws_ssm_parameter.ses_sender_email.arn,
      aws_ssm_parameter.report_recipients.arn,
    ]
  }

  # SES send email
  statement {
    sid    = "AllowSESSend"
    effect = "Allow"
    actions = [
      "ses:SendEmail",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "lambda" {
  name   = "${local.prefix}-lambda-policy"
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.lambda_permissions.json
}

# ---------------------------------------------------------------------------
# DynamoDB Tables
# ---------------------------------------------------------------------------

resource "aws_dynamodb_table" "orders" {
  name             = "orders"
  billing_mode     = var.dynamodb_billing_mode
  hash_key         = "order_id"
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  attribute {
    name = "order_id"
    type = "S"
  }

  point_in_time_recovery {
    enabled = var.environment == "prod"
  }

  tags = {
    Name = "${local.prefix}-orders-table"
  }
}

resource "aws_dynamodb_table" "support_tickets" {
  name             = "support_tickets"
  billing_mode     = var.dynamodb_billing_mode
  hash_key         = "ticket_id"
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  attribute {
    name = "ticket_id"
    type = "S"
  }

  point_in_time_recovery {
    enabled = var.environment == "prod"
  }

  tags = {
    Name = "${local.prefix}-tickets-table"
  }
}

resource "aws_dynamodb_table" "business_metrics" {
  name             = "business_metrics"
  billing_mode     = var.dynamodb_billing_mode
  hash_key         = "metric_id"
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  attribute {
    name = "metric_id"
    type = "S"
  }

  point_in_time_recovery {
    enabled = var.environment == "prod"
  }

  tags = {
    Name = "${local.prefix}-metrics-table"
  }
}

# ---------------------------------------------------------------------------
# SES Email Identity
# ---------------------------------------------------------------------------

resource "aws_ses_email_identity" "sender" {
  email = var.ses_sender_email
}

# For production, consider verifying the domain instead:
# resource "aws_ses_domain_identity" "sender" {
#   domain = "yourdomain.com"
# }

# ---------------------------------------------------------------------------
# Lambda Function
# ---------------------------------------------------------------------------

resource "aws_lambda_function" "report_generator" {
  function_name = local.prefix
  description   = "Scheduled report generator with Claude AI insights"
  runtime       = "python3.11"
  handler       = "handler.lambda_handler"
  memory_size   = var.lambda_memory
  timeout       = var.lambda_timeout
  role          = aws_iam_role.lambda.arn

  filename         = "${path.module}/../dist/lambda.zip"
  source_code_hash = fileexists("${path.module}/../dist/lambda.zip") ? filebase64sha256("${path.module}/../dist/lambda.zip") : null

  environment {
    variables = {
      ENVIRONMENT       = var.environment
      ANTHROPIC_MODEL   = var.anthropic_model
      MAX_TOKENS        = tostring(var.max_tokens)
      REPORT_TYPE       = var.report_type
      TIMEZONE          = var.report_timezone
      ANTHROPIC_API_KEY = var.anthropic_api_key
      LOG_LEVEL         = var.environment == "prod" ? "WARNING" : "INFO"
    }
  }

  depends_on = [
    aws_iam_role_policy.lambda,
    aws_cloudwatch_log_group.lambda,
  ]

  tags = {
    Name = "${local.prefix}-lambda"
  }
}

# ---------------------------------------------------------------------------
# EventBridge Scheduled Rule
# ---------------------------------------------------------------------------

resource "aws_cloudwatch_event_rule" "report_schedule" {
  name                = "${local.prefix}-schedule"
  description         = "Trigger scheduled report generation"
  schedule_expression = "cron(${var.report_schedule_cron})"
  is_enabled          = true

  tags = {
    Name = "${local.prefix}-schedule-rule"
  }
}

resource "aws_cloudwatch_event_target" "lambda" {
  rule      = aws_cloudwatch_event_rule.report_schedule.name
  target_id = "ReportGeneratorLambda"
  arn       = aws_lambda_function.report_generator.arn
  role_arn  = aws_iam_role.eventbridge.arn

  input = jsonencode({
    source      = "aws.events"
    detail-type = "Scheduled Event"
  })
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.report_generator.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.report_schedule.arn
}

# EventBridge role to invoke Lambda
data "aws_iam_policy_document" "eventbridge_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "eventbridge" {
  name               = "${local.prefix}-eventbridge-role"
  assume_role_policy = data.aws_iam_policy_document.eventbridge_assume.json

  tags = {
    Name = "${local.prefix}-eventbridge-role"
  }
}

data "aws_iam_policy_document" "eventbridge_invoke" {
  statement {
    actions = [
      "lambda:InvokeFunction",
    ]
    resources = [aws_lambda_function.report_generator.arn]
  }
}

resource "aws_iam_role_policy" "eventbridge" {
  name   = "${local.prefix}-eventbridge-policy"
  role   = aws_iam_role.eventbridge.id
  policy = data.aws_iam_policy_document.eventbridge_invoke.json
}

# ---------------------------------------------------------------------------
# CloudWatch Alarms
# ---------------------------------------------------------------------------

resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${local.prefix}-lambda-errors"
  alarm_description   = "Alert if Lambda error count exceeds threshold"
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 2
  threshold           = 2
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.report_generator.function_name
  }

  tags = {
    Name = "${local.prefix}-lambda-errors-alarm"
  }
}

resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  alarm_name          = "${local.prefix}-lambda-duration"
  alarm_description   = "Alert if Lambda duration exceeds 80% of timeout"
  namespace           = "AWS/Lambda"
  metric_name         = "Duration"
  extended_statistic  = "p99"
  period              = 300
  evaluation_periods  = 2
  threshold           = var.lambda_timeout * 1000 * 0.8
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.report_generator.function_name
  }

  tags = {
    Name = "${local.prefix}-lambda-duration-alarm"
  }
}

resource "aws_cloudwatch_metric_alarm" "dynamodb_throttle" {
  alarm_name          = "${local.prefix}-dynamodb-throttle"
  alarm_description   = "Alert if DynamoDB is throttled"
  namespace           = "AWS/DynamoDB"
  metric_name         = "UserErrors"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    TableName = aws_dynamodb_table.orders.name
  }

  tags = {
    Name = "${local.prefix}-dynamodb-throttle-alarm"
  }
}
