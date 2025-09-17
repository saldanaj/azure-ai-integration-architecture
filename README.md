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

## Next steps (Azure)
- Fill out `infra/bicep/*.bicep` to deploy: APIM, Event Grid topic/subscription, Azure SQL, Container Apps environment & apps, AI Foundry agent + model.
- Replace local env vars with Managed Identity + Key Vault references.
- Import `apis/*.openapi.yaml` into APIM and apply policies in `infra/apim/policies/`.

