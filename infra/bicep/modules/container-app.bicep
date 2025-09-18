param name string
param location string = resourceGroup().location
param managedEnvironmentId string
param containerImage string
param targetPort int = 80
param ingressExternal bool = false
param ingressTransport string = 'auto'
param allowInsecureIngress bool = false
param minReplicas int = 1
param maxReplicas int = 1
param cpu float = 0.5
param memory string = '1Gi'
param envVars array = []
param secrets array = []
param registries array = []
param tags object = {}
param revisionSuffix string = ''
param daprEnabled bool = false
param scaleRules array = []
param identityType string = 'SystemAssigned'
param userAssignedIdentityResourceIds array = []

var userAssignedIdentities = [for id in userAssignedIdentityResourceIds: { id: id }]
var hasUserAssigned = length(userAssignedIdentityResourceIds) > 0

resource app 'Microsoft.App/containerApps@2023-05-01' = {
  name: name
  location: location
  tags: tags
  identity: {
    type: hasUserAssigned ? (identityType == 'SystemAssigned' ? 'SystemAssigned,UserAssigned' : identityType) : identityType
    userAssignedIdentities: hasUserAssigned ? { for identity in userAssignedIdentities: identity.id : {} } : null
  }
  properties: {
    managedEnvironmentId: managedEnvironmentId
    configuration: {
      ingress: {
        external: ingressExternal
        targetPort: targetPort
        transport: ingressTransport
        allowInsecure: allowInsecureIngress
      }
      registries: registries
      secrets: secrets
      dapr: daprEnabled ? {
        enabled: true
        appPort: targetPort
      } : null
    }
    template: {
      revisionSuffix: empty(revisionSuffix) ? null : revisionSuffix
      containers: [
        {
          name: name
          image: containerImage
          resources: {
            cpu: cpu
            memory: memory
          }
          env: envVars
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
        rules: scaleRules
      }
    }
  }
}

output appId string = app.id
output principalId string = app.identity.principalId
output name string = app.name
