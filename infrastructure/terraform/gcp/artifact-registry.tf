resource "google_artifact_registry_repository" "app" {
  provider      = google
  location      = var.gcp_region
  repository_id = "ai-morphasis"
  description   = "Container images for AI-Morphasis"
  format        = "DOCKER"
  project       = var.gcp_project_id
}
