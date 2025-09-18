# Discharge Copilot + Follow-up Orchestrator (Starter)

End-to-end healthcare demo showcasing **Azure AI Foundry + APIM + Containers + Azure SQL + Event Grid + MCP**.

> Local scaffold: run with Docker Compose. Azure deployment is sketched in Bicep modules (placeholders).

## Quick start (local)
1. **Prereqs:** Docker Desktop, Python 3.11 (optional).
2. `docker compose up -d --build`
3. Open the mock FHIR service at http://localhost:8080/fhir/DocumentReference/D789
4. Send the sample DischargeCreated event (simulate Event Grid):
   ```bash
   curl -X POST http://localhost:7001/events \
     -H "Content-Type: application/json" \
     --data @events/samples/dischargeCreated.json
   ```
5. Watch logs from services:
   ```bash
   docker compose logs -f fhir-listener mcp-server mock-fhir
   ```

## What happens
- **fhir-listener** receives the event (validates handshake or processes payload).
- It calls **mcp-server** tools (stubs) to fetch the FHIR doc, upsert a task, and emit another event (local no-op).
- OpenAPI stubs provided in `apis/` and SQL DDL in `db/`.

## Testing

Run the stdlib test suite (no external deps required):

```bash
python3 -m unittest discover -s tests
```

## Azure deployment (single resource group)

1. **Build & push images** – publish `services/*` containers to your registry (e.g. ACR or GHCR). Capture image tags for Bicep parameters.
2. **Deploy infrastructure** – create a resource group, then run:
   ```bash
   az deployment group create \
     --resource-group <rg-name> \
     --template-file infra/bicep/main.bicep \
     --parameters \
       env=dev \
       mcpServerImage=<registry>/mcp-server:<tag> \
       fhirListenerImage=<registry>/fhir-listener:<tag> \
       tasksApiImage=<registry>/tasks-api:<tag> \
       mockFhirImage=<registry>/mock-fhir:<tag> \# optional \
       sqlAdministratorPassword=<StrongPassword> \
       apimPublisherEmail=<you@example.com> \
       apimPublisherName="Demo Owner"
   ```
   Additional parameters (registry creds, custom names, Key Vault admin object Id, etc.) are documented in `infra/bicep/main.bicep`.
3. **Grant database access** – after deployment, assign the container app managed identity to the SQL database:
   ```sql
   -- Connect using Azure AD admin
   CREATE USER [discharge-copilot-mi] FROM EXTERNAL PROVIDER;
   ALTER ROLE db_datareader ADD MEMBER [discharge-copilot-mi];
   ALTER ROLE db_datawriter ADD MEMBER [discharge-copilot-mi];
   ```
   Replace the identity name with the object supplied in the deployment outputs.
4. **Seed data** – execute `db/ddl.sql` (or load Synthea CSVs) to populate `patients` before firing events.
5. **Trigger the flow** – publish a `DischargeCreated` event to the Event Grid topic endpoint exposed in the outputs. The MCP server now writes to Azure SQL and emits real events.

For parameter descriptions and outputs, see `infra/bicep/README.md`. Import `apis/*.openapi.yaml` into APIM and update policies under `infra/apim/policies/` to enable JWT, rate limits, and masking.
