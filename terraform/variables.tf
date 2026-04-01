###############################################################################
# Scheduled Report Generator — Variables
###############################################################################

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "AWS CLI profile name"
  type        = string
  default     = "default"
}

variable "project_name" {
  description = "Project identifier used in resource naming"
  type        = string
  default     = "scheduled-report-generator"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "uat", "prod"], var.environment)
    error_message = "Environment must be dev, uat, or prod."
  }
}

variable "anthropic_api_key" {
  description = "Anthropic API key — stored encrypted in SSM Parameter Store"
  type        = string
  sensitive   = true
}

variable "anthropic_model" {
  description = "Claude model to use for report generation"
  type        = string
  default     = "claude-sonnet-4-20250514"
}

variable "max_tokens" {
  description = "Maximum output tokens per Claude request"
  type        = number
  default     = 2048
}

variable "ses_sender_email" {
  description = "SES sender email address (must be verified in SES)"
  type        = string
}

variable "report_recipients" {
  description = "Email addresses to receive reports"
  type        = list(string)

  validation {
    condition     = length(var.report_recipients) > 0
    error_message = "At least one recipient email is required."
  }
}

variable "report_schedule_cron" {
  description = "EventBridge cron expression for report schedule (UTC). Example: '0 9 * * *' for daily at 9 AM."
  type        = string
  default     = "0 9 * * *"
}

variable "report_type" {
  description = "Report type: daily_summary, weekly_digest, or monthly_review"
  type        = string
  default     = "daily_summary"

  validation {
    condition     = contains(["daily_summary", "weekly_digest", "monthly_review"], var.report_type)
    error_message = "Report type must be daily_summary, weekly_digest, or monthly_review."
  }
}

variable "report_timezone" {
  description = "IANA timezone for report display (e.g., America/New_York, Europe/London)"
  type        = string
  default     = "America/New_York"
}

variable "lambda_memory" {
  description = "Lambda memory in MB"
  type        = number
  default     = 512
}

variable "lambda_timeout" {
  description = "Lambda timeout in seconds"
  type        = number
  default     = 60
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 14
}

variable "dynamodb_billing_mode" {
  description = "DynamoDB billing mode: PAY_PER_REQUEST or PROVISIONED"
  type        = string
  default     = "PAY_PER_REQUEST"

  validation {
    condition     = contains(["PAY_PER_REQUEST", "PROVISIONED"], var.dynamodb_billing_mode)
    error_message = "Billing mode must be PAY_PER_REQUEST or PROVISIONED."
  }
}
