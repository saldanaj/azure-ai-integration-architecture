param name string
param location string = resourceGroup().location
param tags object = {}
param logAnalyticsCustomerId string
param logAnalyticsSharedKey string
param internalLoadBalancerEnabled bool = false
param workloadProfiles array = [
  {
    name: 'Consumption'
    workloadProfileType: 'Consumption'
  }
]

resource env 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsCustomerId
        sharedKey: logAnalyticsSharedKey
      }
    }
    internalLoadBalancerEnabled: internalLoadBalancerEnabled
    workloadProfiles: workloadProfiles
  }
}

output environmentId string = env.id
output environmentName string = env.name
