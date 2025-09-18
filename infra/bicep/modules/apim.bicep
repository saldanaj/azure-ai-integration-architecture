param name string
param location string = resourceGroup().location
param publisherEmail string
param publisherName string
param skuName string = 'Consumption'
param skuCapacity int = 0
param tags object = {}
param enableClientCertificate bool = false
param virtualNetworkType string = 'None'

resource apim 'Microsoft.ApiManagement/service@2022-08-01' = {
  name: name
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    publisherEmail: publisherEmail
    publisherName: publisherName
    virtualNetworkType: virtualNetworkType
    enableClientCertificate: enableClientCertificate
  }
  sku: {
    name: skuName
    capacity: skuCapacity
  }
}

output serviceId string = apim.id
output gatewayUrl string = apim.properties.gatewayUrl
output developerPortalUrl string = apim.properties.developerPortalUrl
output principalId string = apim.identity.principalId
