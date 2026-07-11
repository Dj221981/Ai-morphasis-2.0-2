# Terraform Deployment Guide

## Initialize
```bash
cd infrastructure/terraform
terraform init
```

## Plan
```bash
terraform plan -var-file=../tfvars/dev.tfvars
```

## Apply
```bash
terraform apply -var-file=../tfvars/dev.tfvars
```

Select provider with `cloud_provider` variable (`aws`, `gcp`, `azure`).
