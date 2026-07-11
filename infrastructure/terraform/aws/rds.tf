resource "aws_db_subnet_group" "this" {
  count      = var.enable_rds ? 1 : 0
  name       = "${var.project_name}-${var.environment}-db-subnet"
  subnet_ids = [aws_subnet.private_a.id, aws_subnet.private_b.id]
}

resource "aws_db_instance" "metadata" {
  count                  = var.enable_rds ? 1 : 0
  identifier             = "${var.project_name}-${var.environment}-metadata"
  allocated_storage      = 20
  engine                 = "postgres"
  engine_version         = "16"
  instance_class         = "db.t3.micro"
  db_name                = "ai_morphasis"
  username               = "ai_morphasis"
  password               = var.db_password
  skip_final_snapshot    = true
  db_subnet_group_name   = aws_db_subnet_group.this[0].name
  publicly_accessible    = false
  deletion_protection    = var.rds_deletion_protection
}
