# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an Azure AI integration architecture demo showcasing a healthcare discharge copilot and follow-up orchestrator. The system demonstrates event-driven processing using **Azure AI Foundry + APIM + Containers + Azure SQL + Event Grid + MCP (Model Context Protocol)**.

The architecture processes discharge events, extracts follow-up tasks using AI, and manages task orchestration through a microservices architecture.

## Architecture

### Core Services
- **fhir-listener** (`services/fhir-listener/`): Flask-based event processor that receives DischargeCreated events, validates Event Grid handshakes, and orchestrates MCP tool calls
- **mcp-server** (`services/mcp-server/`): FastMCP server providing tools for FHIR document retrieval, task management, and Event Grid publishing
- **mock-fhir** (`services/mock-fhir/`): Flask service simulating FHIR DocumentReference endpoints for local development

### Key Directories
- `ai/`: AI agent configuration and prompts for discharge processing
- `apis/`: OpenAPI specifications for copilot and tasks services
- `events/`: JSON schemas and sample events for Event Grid integration
- `infra/`: Bicep templates for Azure deployment (placeholder implementations)
- `db/`: SQL DDL scripts for task management tables
- `ops/`: Operational scripts and Makefiles

### Event Flow
1. DischargeCreated event → fhir-listener
2. fhir-listener calls MCP tools to fetch FHIR document
3. AI processing extracts follow-up tasks (stubbed locally)
4. Tasks are upserted and TaskCreated events are emitted

## Development Commands

### Local Development
```bash
# Start all services
docker compose up -d --build

# Or use the Makefile
make up

# View logs
docker compose logs -f fhir-listener mcp-server mock-fhir
make logs

# Stop services
docker compose down -v
make down
```

### Testing the System
```bash
# Test mock FHIR service
curl http://localhost:8080/fhir/DocumentReference/D789

# Send sample discharge event
curl -X POST http://localhost:7001/events \
  -H "Content-Type: application/json" \
  --data @events/samples/dischargeCreated.json
```

### Service Endpoints
- Mock FHIR: http://localhost:8080
- FHIR Listener: http://localhost:7001
- MCP Server: http://localhost:9000

## Azure Deployment

The project includes Bicep templates in `infra/bicep/` for Azure deployment. Key Azure services to be configured:
- Azure AI Foundry (agent + model deployment)
- API Management (import OpenAPI specs from `apis/`)
- Event Grid (topic/subscription setup)
- Azure SQL Database (task management)
- Container Apps (service hosting)
- Managed Identity + Key Vault (authentication)

## MCP Integration

The MCP server exposes these tools:
- `get_fhir_document`: Retrieves FHIR DocumentReference
- `upsert_task`: Manages follow-up tasks in database
- `emit_eventgrid`: Publishes events to Event Grid
- `phi_scrub`: Basic PII/PHI scrubbing for data protection

## Technology Stack

- **Python 3.11+** with Flask/FastMCP frameworks
- **Docker Compose** for local orchestration
- **Azure services** for cloud deployment
- **Event Grid** for event-driven architecture
- **FHIR R4** for healthcare data standards
- **MCP** for AI agent tool integration

## Development Environment

A `.devcontainer` is provided with:
- Azure CLI with Bicep extension
- Python venv setup with consolidated requirements
- Azure Functions Core Tools v4
- Node.js and npm for additional tooling