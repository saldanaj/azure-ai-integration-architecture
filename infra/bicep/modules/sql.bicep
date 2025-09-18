param serverName string
param databaseName string
param location string = resourceGroup().location
param administratorLogin string
@secure()
param administratorPassword string
param skuName string = 'GP_S_Gen5_1'
param maxSizeGb int = 2
@minValue(10)
param autoPauseDelayMinutes int = 60
@minValue(1)
param minCapacity float = 0.5
param tags object = {}
param enablePublicNetwork bool = true
param allowAzureServices bool = true
param aadAdminLogin string = ''
param aadAdminObjectId string = ''
param aadTenantId string = tenant().tenantId

var maxSizeBytes = int(maxSizeGb) * 1024 * 1024 * 1024

resource sqlServer 'Microsoft.Sql/servers@2022-05-01-preview' = {
  name: serverName
  location: location
  tags: tags
  properties: {
    administratorLogin: administratorLogin
    administratorLoginPassword: administratorPassword
    publicNetworkAccess: enablePublicNetwork ? 'Enabled' : 'Disabled'
    minimalTlsVersion: '1.2'
  }
}

resource sqlDatabase 'Microsoft.Sql/servers/databases@2022-05-01-preview' = {
  name: '${sqlServer.name}/${databaseName}'
  location: location
  sku: {
    name: skuName
    tier: 'GeneralPurpose'
    family: 'Gen5'
    capacity: 0
  }
  properties: {
    autoPauseDelay: autoPauseDelayMinutes
    minCapacity: minCapacity
    requestedServiceObjectiveName: skuName
    maxSizeBytes: maxSizeBytes
  }
}

resource firewallAzureServices 'Microsoft.Sql/servers/firewallRules@2022-05-01-preview' = if (allowAzureServices) {
  name: '${sqlServer.name}/AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

resource aadAdmin 'Microsoft.Sql/servers/administrators@2022-05-01-preview' = if (!empty(aadAdminLogin) && !empty(aadAdminObjectId)) {
  name: '${sqlServer.name}/activeDirectory'
  properties: {
    administratorType: 'ActiveDirectory'
    login: aadAdminLogin
    sid: aadAdminObjectId
    tenantId: aadTenantId
    azureADOnlyAuthentication: true
  }
}

output serverName string = sqlServer.name
output serverResourceId string = sqlServer.id
output databaseName string = sqlDatabase.name
output databaseResourceId string = sqlDatabase.id
