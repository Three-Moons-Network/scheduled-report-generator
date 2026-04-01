###############################################################################
# Scheduled Report Generator — Outputs
###############################################################################

output "lambda_function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.report_generator.function_name
}

output "lambda_function_arn" {
  description = "Lambda function ARN"
  value       = aws_lambda_function.report_generator.arn
}

output "eventbridge_rule_name" {
  description = "EventBridge rule name for report schedule"
  value       = aws_cloudwatch_event_rule.report_schedule.name
}

output "eventbridge_rule_arn" {
  description = "EventBridge rule ARN"
  value       = aws_cloudwatch_event_rule.report_schedule.arn
}

output "eventbridge_rule_schedule" {
  description = "EventBridge cron schedule expression"
  value       = aws_cloudwatch_event_rule.report_schedule.schedule_expression
}

output "orders_table_name" {
  description = "DynamoDB orders table name"
  value       = aws_dynamodb_table.orders.name
}

output "tickets_table_name" {
  description = "DynamoDB support_tickets table name"
  value       = aws_dynamodb_table.support_tickets.name
}

output "metrics_table_name" {
  description = "DynamoDB business_metrics table name"
  value       = aws_dynamodb_table.business_metrics.name
}

output "ses_sender_identity" {
  description = "SES sender email identity"
  value       = aws_ses_email_identity.sender.email
}

output "cloudwatch_log_group" {
  description = "Lambda CloudWatch log group name"
  value       = aws_cloudwatch_log_group.lambda.name
}

output "lambda_role_arn" {
  description = "Lambda execution role ARN"
  value       = aws_iam_role.lambda.arn
}

output "ssm_parameter_api_key" {
  description = "SSM parameter name for Anthropic API key"
  value       = aws_ssm_parameter.anthropic_api_key.name
}

output "ssm_parameter_recipients" {
  description = "SSM parameter name for report recipients"
  value       = aws_ssm_parameter.report_recipients.name
}

output "ssm_parameter_sender_email" {
  description = "SSM parameter name for SES sender email"
  value       = aws_ssm_parameter.ses_sender_email.name
}
