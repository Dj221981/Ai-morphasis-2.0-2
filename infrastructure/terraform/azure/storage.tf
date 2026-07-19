resource "azurerm_storage_account" "artifacts" {
  name                     = "aimorphasis${var.environment}sa"
  resource_group_name      = azurerm_resource_group.this.name
  location                 = azurerm_resource_group.this.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

resource "azurerm_storage_container" "models" {
  name                  = "model-artifacts"
  storage_account_name  = azurerm_storage_account.artifacts.name
  container_access_type = "private"
}
