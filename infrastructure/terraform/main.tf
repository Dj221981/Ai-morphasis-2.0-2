locals {
  common_tags = {
    project     = var.project_name
    environment = var.environment
    managed_by  = "terraform"
  }
}

module "aws" {
  source = "./aws"
  count  = var.cloud_provider == "aws" ? 1 : 0

  project_name = var.project_name
  environment  = var.environment
  aws_region   = var.aws_region
  db_password  = var.db_password
}

module "gcp" {
  source = "./gcp"
  count  = var.cloud_provider == "gcp" ? 1 : 0

  project_name   = var.project_name
  environment    = var.environment
  gcp_project_id = var.gcp_project_id
  gcp_region     = var.gcp_region
}

module "azure" {
  source = "./azure"
  count  = var.cloud_provider == "azure" ? 1 : 0

  project_name          = var.project_name
  environment           = var.environment
  azure_region          = var.azure_region
  azure_subscription_id = var.azure_subscription_id
}
