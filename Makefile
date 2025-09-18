COMPOSE ?= docker compose

.PHONY: up down logs

up:
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down

logs:
	@services="$(SERVICES)"; \
	if [ -n "$$services" ]; then \
		$(COMPOSE) logs -f $$services; \
	else \
		$(COMPOSE) logs -f fhir-listener mcp-server mock-fhir; \
	fi
