param name string
param tenantId string
param location string = resourceGroup().location
param skuName string = 'standard'
param enablePurgeProtection bool = false
param enableRbacAuthorization bool = false
param softDeleteRetentionDays int = 7
param accessPolicies array = []
param tags object = {}

resource vault 'Microsoft.KeyVault/vaults@2022-07-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    tenantId: tenantId
    enablePurgeProtection: enablePurgeProtection
    enableSoftDelete: true
    softDeleteRetentionInDays: softDeleteRetentionDays
    enableRbacAuthorization: enableRbacAuthorization
    sku: {
      name: skuName
      family: 'A'
    }
    accessPolicies: accessPolicies
  }
}

output vaultId string = vault.id
output vaultUri string = vault.properties.vaultUri
