param name string
param location string = resourceGroup().location
param inputSchema string = 'EventGridSchema'
param publicNetworkAccess string = 'Enabled'
param tags object = {}

resource topic 'Microsoft.EventGrid/topics@2022-06-15' = {
  name: name
  location: location
  tags: tags
  properties: {
    inputSchema: inputSchema
    publicNetworkAccess: publicNetworkAccess
  }
}

var keys = listKeys(topic.id, topic.apiVersion)

output topicId string = topic.id
output endpoint string = topic.properties.endpoint
@secure()
output primaryKey string = keys.key1
@secure()
output secondaryKey string = keys.key2
