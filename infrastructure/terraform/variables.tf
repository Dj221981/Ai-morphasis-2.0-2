variable "project_name" { type = string }
variable "environment" { type = string }
variable "cloud_provider" {
  type    = string
  default = "aws"
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}
variable "gcp_project_id" {
  type    = string
  default = ""
}
variable "gcp_region" {
  type    = string
  default = "us-central1"
}
variable "azure_subscription_id" {
  type    = string
  default = ""
}
variable "azure_region" {
  type    = string
  default = "eastus"
}
variable "db_password" {
  type      = string
  sensitive = true
  default   = ""
  validation {
    condition     = var.cloud_provider != "aws" || !var.enable_rds || length(var.db_password) >= 12
    error_message = "db_password must be at least 12 characters when enable_rds is true on aws."
  }
}
variable "enable_rds" {
  type    = bool
  default = false
}
variable "rds_deletion_protection" {
  type    = bool
  default = false
}
