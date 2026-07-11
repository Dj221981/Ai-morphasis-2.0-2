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
}
