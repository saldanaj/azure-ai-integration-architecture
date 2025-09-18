# Azure Bicep deployment

`main.bicep` provisions all core resources for the Discharge Copilot demo inside a single resource group.

## Modules
- **Managed identity** shared by the container apps (`modules/managed-identity.bicep`).
- **Log Analytics workspace** and container apps environment (`modules/log-analytics.bicep`, `modules/container-app-environment.bicep`).
- **Key Vault** for secrets and configuration (`modules/key-vault.bicep`).
- **Azure SQL server/database** with serverless SKU defaults (`modules/sql.bicep`).
- **Event Grid custom topic** (`modules/event-grid.bicep`).
- **API Management Consumption tier** (`modules/apim.bicep`).
- **Container Apps** for `mcp-server`, `fhir-listener`, `tasks-api`, and optional `mock-fhir` (`modules/container-app.bicep`).

## Key parameters
| Name | Description |
| --- | --- |
| `env` | Logical environment suffix used for naming (default `dev`). |
| `sqlAdministratorPassword` | Required bootstrap password for SQL admin. Rotate after deployment. |
| `apimPublisherEmail` / `apimPublisherName` | Required for APIM provisioning. |
| `mcpServerImage`, `fhirListenerImage`, `tasksApiImage`, `mockFhirImage` | Container image references to deploy. |
| `containerRegistry*` | Optional registry server/user/password if images are private. |
| `keyVaultAdminObjectId` | Optional AAD object ID granted initial Key Vault secret access. |
| `publicIngress` | Exposes container apps publicly when `true`. Leave `false` for private ingress. |

Full parameter list is annotated inside `main.bicep`.

## Outputs
- `managedEnvironmentId` – Container Apps environment resource ID.
- `sqlServerFqdn` – Fully-qualified SQL server hostname.
- `keyVaultUri` – Base URI for retrieving secrets.
- `eventGridEndpoint` – HTTPS endpoint for publishing events.
- `apimGatewayUrl` – Public APIM gateway URL.
- `mcpPrincipalId` and `identityClientId` – Use when granting database or Key Vault access.

## Post-deployment steps
1. **Grant SQL permissions**: connect as the Azure AD admin and create a contained user for the managed identity, granting `db_datareader` and `db_datawriter` (see root `README.md`).
2. **Populate data**: run `db/ddl.sql` and load Synthea exports (CSV/JSON) into Azure SQL if you need reference patient rows.
3. **Secrets**: add Event Grid keys or other secrets to Key Vault as needed; container apps already have access via the managed identity.
4. **APIM policies**: import `apis/tasks.openapi.yaml` and `apis/copilot.openapi.yaml`, then apply JWT, rate limiting, and masking policies referenced in `infra/apim/policies/`.
5. **Networking (optional)**: integrate Container Apps environment with a VNet and enable private endpoints for SQL/Key Vault when moving beyond the demo subnet.

## Validation
Use the deployment outputs to:
- Publish the sample `events/samples/dischargeCreated.json` payload to Event Grid (set the correct `topicEndpoint`).
- Query `care_tasks` in Azure SQL to confirm inserts and audit records are created.
- Hit `/patients/{patientId}/tasks` through APIM once wired to the tasks API.

The local Docker Compose loop remains available for offline development; switch `TASK_DB_MODE` to `sqlite` to fall back to the local task store.
