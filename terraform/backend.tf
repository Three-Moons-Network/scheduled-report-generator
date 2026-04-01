###############################################################################
# Scheduled Report Generator — Backend Configuration
#
# Uncomment to enable remote state storage in S3.
# For local development, comment this out to use local terraform.tfstate.
###############################################################################

# terraform {
#   backend "s3" {
#     bucket         = "your-terraform-state-bucket"
#     key            = "scheduled-report-generator/terraform.tfstate"
#     region         = "us-east-1"
#     encrypt        = true
#     dynamodb_table = "terraform-locks"
#   }
# }
