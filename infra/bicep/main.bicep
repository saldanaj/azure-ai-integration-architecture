@description('Deployment environment identifier (e.g. dev, test, prod). Used in resource naming.')
param env string = 'dev'

@description('Azure region for resources.')
param location string = resourceGroup().location

@description('Short prefix applied to resource names.')
param namePrefix string = 'dcopilot'

@description('Tags applied to all resources.')
param tags object = {
  environment: env
}

@description('SQL administrator login (used for bootstrap; rotate after deployment).')
param sqlAdministratorLogin string = 'sqldemoadmin'

@secure()
@description('SQL administrator password.')
param sqlAdministratorPassword string

@description('Azure AD login and object id for SQL Active Directory admin (optional).')
param sqlAadAdminLogin string = ''
param sqlAadAdminObjectId string = ''

@description('Logical SQL database name.')
param sqlDatabaseName string = 'caretasks'

@description('Override names for resources (leave empty to auto-generate).')
param logAnalyticsName string = ''
param containerAppsEnvironmentName string = ''
param userAssignedIdentityName string = ''
param keyVaultName string = ''
param sqlServerName string = ''
param eventGridTopicName string = ''
param apimName string = ''

@description('API Management publisher metadata.')
param apimPublisherEmail string
param apimPublisherName string

@description('Container registry settings (optional if using public images).')
param containerRegistryServer string = ''
param containerRegistryUsername string = ''
@secure()
param containerRegistryPassword string = ''

@description('Container images for services.')
param mcpServerImage string
param fhirListenerImage string
param tasksApiImage string
param mockFhirImage string = ''

@description('Enable external ingress for container apps (set true for public endpoints).')
param publicIngress bool = false

@description('Object ID of the operator/service principal granted initial Key Vault access (optional).')
param keyVaultAdminObjectId string = ''

var suffix = toLower(uniqueString(resourceGroup().id, env))
var sanitizedPrefix = toLower(replace(replace(namePrefix, ' ', ''), '_', ''))
var base = '${sanitizedPrefix}-${env}'

var effectiveLogAnalyticsName = empty(logAnalyticsName) ? take('${base}-law-${suffix}', 63) : logAnalyticsName
var effectiveContainerEnvName = empty(containerAppsEnvironmentName) ? take('${base}-cae-${suffix}', 63) : containerAppsEnvironmentName
var effectiveIdentityName = empty(userAssignedIdentityName) ? take('${base}-id-${suffix}', 64) : userAssignedIdentityName
var effectiveSqlServerName = empty(sqlServerName) ? take('${sanitizedPrefix}-${env}-${suffix}-sql', 60) : sqlServerName
var effectiveSqlServerNameSanitized = toLower(replace(effectiveSqlServerName, '_', ''))
var effectiveEventGridTopicName = empty(eventGridTopicName) ? take('${base}-evt-${suffix}', 50) : eventGridTopicName
var keyVaultBase = replace('${sanitizedPrefix}${env}${suffix}', '-', '')
var effectiveKeyVaultName = empty(keyVaultName) ? take(keyVaultBase, 24) : keyVaultName
var effectiveApimName = empty(apimName) ? take('${sanitizedPrefix}-${env}-${suffix}', 50) : apimName

var registrySecretName = 'registry-password'
var eventGridSecretName = 'eventgrid-key'
var commonTags = union(tags, {
  workload: 'discharge-copilot'
})

module identity './modules/managed-identity.bicep' = {
  name: 'identity-${env}'
  params: {
    name: effectiveIdentityName
    location: location
    tags: commonTags
  }
}

module logAnalytics './modules/log-analytics.bicep' = {
  name: 'law-${env}'
  params: {
    name: effectiveLogAnalyticsName
    location: location
    tags: commonTags
  }
}

resource existingWorkspace 'Microsoft.OperationalInsights/workspaces@2022-10-01' existing = {
  id: logAnalytics.outputs.workspaceId
}

var workspaceKeys = listKeys(existingWorkspace.id, existingWorkspace.apiVersion)

module containerEnv './modules/container-app-environment.bicep' = {
  name: 'cae-${env}'
  params: {
    name: effectiveContainerEnvName
    location: location
    tags: commonTags
    logAnalyticsCustomerId: logAnalytics.outputs.customerId
    logAnalyticsSharedKey: workspaceKeys.primarySharedKey
  }
}

var defaultKvPolicies = empty(keyVaultAdminObjectId) ? [] : [
  {
    tenantId: tenant().tenantId
    objectId: keyVaultAdminObjectId
    permissions: {
      secrets: [
        'get'
        'set'
        'list'
        'delete'
      ]
    }
  }
]

var identityPolicy = {
  tenantId: tenant().tenantId
  objectId: identity.outputs.principalId
  permissions: {
    secrets: [
      'get'
      'list'
    ]
  }
}

var keyVaultPolicies = concat(defaultKvPolicies, [identityPolicy])

module vault './modules/key-vault.bicep' = {
  name: 'kv-${env}'
  params: {
    name: effectiveKeyVaultName
    location: location
    tenantId: tenant().tenantId
    accessPolicies: keyVaultPolicies
    tags: commonTags
  }
}

module sql './modules/sql.bicep' = {
  name: 'sql-${env}'
  params: {
    serverName: effectiveSqlServerNameSanitized
    databaseName: sqlDatabaseName
    location: location
    administratorLogin: sqlAdministratorLogin
    administratorPassword: sqlAdministratorPassword
    aadAdminLogin: sqlAadAdminLogin
    aadAdminObjectId: sqlAadAdminObjectId
    tags: commonTags
  }
}

var sqlFqdn = '${sql.outputs.serverName}.database.windows.net'

module eventGrid './modules/event-grid.bicep' = {
  name: 'evt-${env}'
  params: {
    name: effectiveEventGridTopicName
    location: location
    tags: commonTags
  }
}

module apim './modules/apim.bicep' = {
  name: 'apim-${env}'
  params: {
    name: effectiveApimName
    location: location
    tags: commonTags
    publisherEmail: apimPublisherEmail
    publisherName: apimPublisherName
  }
}

var registrySecret = empty(containerRegistryPassword) ? [] : [
  {
    name: registrySecretName
    value: containerRegistryPassword
  }
]

var registryConfig = empty(containerRegistryServer) ? [] : [
  empty(containerRegistryPassword) ? {
    server: containerRegistryServer
    username: containerRegistryUsername
  } : {
    server: containerRegistryServer
    username: containerRegistryUsername
    passwordSecretRef: registrySecretName
  }
]

var mcpSecrets = concat(registrySecret, [
  {
    name: eventGridSecretName
    value: eventGrid.outputs.primaryKey
  }
])

var sharedEnvVars = [
  {
    name: 'SAFE_MODE'
    value: 'true'
  }
  {
    name: 'SQL_SERVER'
    value: sqlFqdn
  }
  {
    name: 'SQL_DATABASE'
    value: sqlDatabaseName
  }
  {
    name: 'AZURE_CLIENT_ID'
    value: identity.outputs.clientId
  }
]

var mcpEnv = concat(sharedEnvVars, [
  {
    name: 'TASK_DB_MODE'
    value: 'azure-sql'
  }
  {
    name: 'EVENTGRID_TOPIC_URL'
    value: eventGrid.outputs.endpoint
  }
  {
    name: 'EVENTGRID_KEY'
    secretRef: eventGridSecretName
  }
])

var fhirEnv = concat(sharedEnvVars, [
  {
    name: 'MCP_URL'
    value: 'http://mcp-server:9000/mcp'
  }
])

var tasksEnv = concat(sharedEnvVars, [
  {
    name: 'PORT'
    value: '8080'
  }
])

var mockFhirEnv = [
  {
    name: 'PORT'
    value: '8080'
  }
]

module mcp './modules/container-app.bicep' = {
  name: 'mcp-${env}'
  params: {
    name: 'mcp-server'
    location: location
    managedEnvironmentId: containerEnv.outputs.environmentId
    containerImage: mcpServerImage
    targetPort: 9000
    ingressExternal: publicIngress
    envVars: mcpEnv
    secrets: mcpSecrets
    registries: registryConfig
    userAssignedIdentityResourceIds: [identity.outputs.identityId]
    identityType: 'UserAssigned'
    tags: commonTags
  }
}

module fhirListener './modules/container-app.bicep' = {
  name: 'fhir-${env}'
  params: {
    name: 'fhir-listener'
    location: location
    managedEnvironmentId: containerEnv.outputs.environmentId
    containerImage: fhirListenerImage
    targetPort: 7001
    ingressExternal: publicIngress
    envVars: fhirEnv
    secrets: registrySecret
    registries: registryConfig
    userAssignedIdentityResourceIds: [identity.outputs.identityId]
    identityType: 'UserAssigned'
    tags: commonTags
  }
}

module tasksApi './modules/container-app.bicep' = {
  name: 'tasks-${env}'
  params: {
    name: 'tasks-api'
    location: location
    managedEnvironmentId: containerEnv.outputs.environmentId
    containerImage: tasksApiImage
    targetPort: 8080
    ingressExternal: publicIngress
    envVars: tasksEnv
    secrets: registrySecret
    registries: registryConfig
    userAssignedIdentityResourceIds: [identity.outputs.identityId]
    identityType: 'UserAssigned'
    tags: commonTags
  }
}

module mockFhir './modules/container-app.bicep' = if (!empty(mockFhirImage)) {
  name: 'mockfhir-${env}'
  params: {
    name: 'mock-fhir'
    location: location
    managedEnvironmentId: containerEnv.outputs.environmentId
    containerImage: mockFhirImage
    targetPort: 8080
    ingressExternal: false
    envVars: mockFhirEnv
    secrets: registrySecret
    registries: registryConfig
    userAssignedIdentityResourceIds: [identity.outputs.identityId]
    identityType: 'UserAssigned'
    tags: commonTags
  }
}

output managedEnvironmentId string = containerEnv.outputs.environmentId
output keyVaultUri string = vault.outputs.vaultUri
output sqlServerFqdn string = sqlFqdn
output sqlDatabaseId string = sql.outputs.databaseResourceId
output eventGridEndpoint string = eventGrid.outputs.endpoint
output apimGatewayUrl string = apim.outputs.gatewayUrl
output mcpPrincipalId string = mcp.outputs.principalId
output identityClientId string = identity.outputs.clientId
