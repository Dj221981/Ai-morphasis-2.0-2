resource "google_storage_bucket" "model_artifacts" {
  name          = "${var.project_name}-${var.environment}-model-artifacts"
  location      = var.gcp_region
  project       = var.gcp_project_id
  force_destroy = false
  versioning {
    enabled = true
  }
}
