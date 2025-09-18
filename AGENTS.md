# Repository Guidelines

## Project Structure & Module Organization
`services/` hosts Python microservices; each service ships its own `Dockerfile` and entrypoint (see `services/fhir-listener/app.py`), while shared helpers live in `services/common/`. API contracts sit in `apis/`, `db/ddl.sql` captures the Azure SQL schema, and `events/samples/` plus `events/schemas/` provide payload fixtures. Infrastructure lives in `infra/bicep/` with APIM policies under `infra/apim/`. Unit tests stay under `tests/`; mirror new modules with matching `tests/test_*.py` files.

## Build, Test, and Development Commands
`make up` (alias for `docker compose up -d --build`) builds and starts the stack. Tail workflows with `docker compose logs -f fhir-listener mcp-server mock-fhir` or set `SERVICES=<name>` for narrower output. Shut everything down with `make down`. Run `python3 -m unittest discover -s tests` before committing changes.

## Coding Style & Naming Conventions
Target Python 3.11 and PEP 8 defaults: 4-space indentation, snake_case functions, CamelCase classes. Keep services self-contained and prefer dependency injection over module-level state, following the `fhir-listener` pattern. Document public helpers with concise docstrings and add type hints on new code paths. No formatter is enforced; if you rely on `black`, keep the default 88-character width across touched files.

## Testing Guidelines
Follow the structure in `tests/test_extractor.py` and `tests/test_extraction_golden.py` for fixtures and assertions. Name tests `test_<feature>_<scenario>` and colocate mock payloads under `events/samples/` when adding new fixtures. Every code change needs a matching regression test or a short note explaining existing coverage, covering both success and failure cases. Installing `requirements-dev.txt` lets you run `pytest` for richer reporting while remaining compatible with the unittest suite.

## Commit & Pull Request Guidelines
Write imperative, scope-aware commit subjects such as `Add task store upsert guard`, and keep bodies focused on intent plus side effects. PRs should link to issues or Azure Boards items, call out dependent Bicep or APIM changes, and include screenshots for updates under `services/web`. Add validation notes that list the commands you ran and summarize API responses if relevant. Request review from the owning service team (FHIR, MCP, Tasks) and confirm secrets stay outside tracked files.

## Deployment & Environment Tips
Review `infra/bicep/README.md` before editing infrastructure and update parameter docs alongside code. Store local secrets in untracked `.env` files consumed by Docker Compose. Rotate sample data in `local-data/` to avoid PHI and keep demos realistic.
