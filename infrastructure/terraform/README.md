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

Enable optional AWS RDS only when needed:
```bash
export TF_VAR_enable_rds=true
export TF_VAR_db_password='<set-securely>'
terraform apply -var-file=../tfvars/prod.tfvars -var='cloud_provider=aws'
```

Select provider with `cloud_provider` variable (`aws`, `gcp`, `azure`).
