// AI Hedge Fund Dashboard - Static Web App Infrastructure
// This Bicep template creates the Azure Static Web App for the dashboard UI

param staticWebAppName string = 'aihedgefund-dashboard'
param location string = 'westeurope'
param sku string = 'Free'
param repositoryUrl string = ''
param branch string = 'main'
param tags object = {
  Project: 'AI-Hedge-Fund'
  Component: 'Dashboard'
  Environment: 'Production'
}

resource staticWebApp 'Microsoft.Web/staticSites@2023-01-01' = if (repositoryUrl != '') {
  name: staticWebAppName
  location: location
  tags: tags
  sku: {
    name: sku
    tier: sku
  }
  properties: {
    repositoryUrl: repositoryUrl
    branch: branch
    stagingEnvironmentPolicy: 'Enabled'
    allowConfigFileUpdates: true
    provider: 'GitHub'
    buildProperties: {
      appLocation: '/dashboard'
      apiLocation: ''
      outputLocation: 'dist'
    }
  }
}

resource staticWebAppManual 'Microsoft.Web/staticSites@2023-01-01' = if (repositoryUrl == '') {
  name: staticWebAppName
  location: location
  tags: tags
  sku: {
    name: sku
    tier: sku
  }
  properties: {
    stagingEnvironmentPolicy: 'Enabled'
    allowConfigFileUpdates: true
  }
}

output staticWebAppId string = repositoryUrl != '' ? staticWebApp!.id : staticWebAppManual!.id
output staticWebAppDefaultHostname string = repositoryUrl != '' ? staticWebApp!.properties.defaultHostname : staticWebAppManual!.properties.defaultHostname
output staticWebAppName string = repositoryUrl != '' ? staticWebApp!.name : staticWebAppManual!.name
