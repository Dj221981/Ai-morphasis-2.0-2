variable "project_name" { type = string }
variable "environment" { type = string }
variable "azure_region" { type = string }
variable "azure_subscription_id" { type = string }

resource "azurerm_resource_group" "this" {
  name     = "${var.project_name}-${var.environment}-rg"
  location = var.azure_region
}

resource "azurerm_kubernetes_cluster" "this" {
  name                = "${var.project_name}-${var.environment}-aks"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  dns_prefix          = "${var.project_name}-${var.environment}"

  default_node_pool {
    name       = "default"
    node_count = 2
    vm_size    = "Standard_D2s_v3"
  }

  identity {
    type = "SystemAssigned"
  }
}
