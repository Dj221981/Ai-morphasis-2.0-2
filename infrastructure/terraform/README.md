# Terraform Deployment Guide

## Initialize
```bash
cd infrastructure/terraform
terraform init
```

## Plan
```bash
export TF_VAR_db_password='<set-securely>'
terraform plan -var-file=../tfvars/dev.tfvars
```

## Apply
```bash
export TF_VAR_db_password='<set-securely>'
terraform apply -var-file=../tfvars/dev.tfvars
```

Select provider with `cloud_provider` variable (`aws`, `gcp`, `azure`).
