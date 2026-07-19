variable "project_name" { type = string }
variable "environment" { type = string }
variable "gcp_project_id" { type = string }
variable "gcp_region" { type = string }

resource "google_container_cluster" "this" {
  name     = "${var.project_name}-${var.environment}-gke"
  location = var.gcp_region
  project  = var.gcp_project_id
  remove_default_node_pool = true
  initial_node_count       = 1
}

resource "google_container_node_pool" "default" {
  name       = "default-pool"
  location   = var.gcp_region
  cluster    = google_container_cluster.this.name
  project    = var.gcp_project_id
  node_count = 2

  node_config {
    machine_type = "e2-standard-2"
  }
}
