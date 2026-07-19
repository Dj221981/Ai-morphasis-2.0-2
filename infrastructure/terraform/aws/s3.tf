resource "aws_s3_bucket" "model_artifacts" {
  bucket = "${var.project_name}-${var.environment}-model-artifacts"
}

resource "aws_s3_bucket_versioning" "model_artifacts" {
  bucket = aws_s3_bucket.model_artifacts.id
  versioning_configuration {
    status = "Enabled"
  }
}
