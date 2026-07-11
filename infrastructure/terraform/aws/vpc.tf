variable "project_name" { type = string }
variable "environment" { type = string }
variable "aws_region" { type = string }
variable "db_password" {
  type      = string
  sensitive = true
}

resource "aws_vpc" "this" {
  cidr_block           = "10.40.0.0/16"
  enable_dns_hostnames = true
  tags = {
    Name = "${var.project_name}-${var.environment}-vpc"
  }
}

resource "aws_subnet" "private_a" {
  vpc_id            = aws_vpc.this.id
  cidr_block        = "10.40.1.0/24"
  availability_zone = "${var.aws_region}a"
  tags = {
    Name = "${var.project_name}-${var.environment}-private-a"
  }
}
