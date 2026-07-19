resource "azurerm_application_insights" "this" {
  name                = "${var.project_name}-${var.environment}-appi"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  application_type    = "web"
}
