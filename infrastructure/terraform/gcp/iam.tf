resource "google_service_account" "workload" {
  account_id   = "ai-morphasis-workload"
  display_name = "AI Morphasis workload"
  project      = var.gcp_project_id
}

resource "google_project_iam_member" "storage_admin" {
  project = var.gcp_project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.workload.email}"
}
