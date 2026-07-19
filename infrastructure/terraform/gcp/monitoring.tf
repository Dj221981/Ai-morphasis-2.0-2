resource "google_monitoring_alert_policy" "high_cpu" {
  display_name = "AI Morphasis High CPU"
  combiner     = "OR"
  conditions {
    display_name = "CPU threshold"
    condition_threshold {
      filter          = "metric.type=\"kubernetes.io/container/cpu/core_usage_time\""
      comparison      = "COMPARISON_GT"
      threshold_value = 0.8
      duration        = "300s"
      trigger {
        count = 1
      }
    }
  }
  project = var.gcp_project_id
}
