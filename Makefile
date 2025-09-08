PATH := /usr/local/bin:$(PATH)

.PHONY: help
help:
	@echo "Cage Repository Service - Available Commands:"
	@echo ""
	@echo "  make install              - Install dependencies"
	@echo "  make serve REPO=<path>    - Start service for specific repository"
	@echo "  make api-start            - Start API service container"
	@echo "  make api-stop             - Stop API service container"
	@echo "  make api-status           - Check API service status"
	@echo "  make test                 - Run API tests"
	@echo "  make test-e2e             - Run end-to-end tests"
	@echo "  make tail-logs            - Follow API logs"
	@echo "  make actor-smoke          - Run actor smoke test"
	@echo "  make setup-gemini         - Setup Gemini configuration"
	@echo ""
	@echo "Examples:"
	@echo "  make serve REPO=/path/to/my-repo"
	@echo "  make serve REPO=./current-directory"

.PHONY: install
install:
	devbox run -- uv pip install -r requirements.txt

.PHONY: api-start
api-start:
	devbox run -- uv run python ./manage.py start

.PHONY: api-stop
api-stop:
	devbox run -- uv run python ./manage.py stop

.PHONY: api-status
api-status:
	devbox run -- uv run python ./manage.py status

.PHONY: serve
serve:
	@if [ -z "$(REPO)" ]; then \
		echo "Error: REPO variable is required. Usage: make serve REPO=/path/to/repository"; \
		exit 1; \
	fi
	@if [ ! -d "$(REPO)" ]; then \
		echo "Error: Repository path does not exist: $(REPO)"; \
		exit 1; \
	fi
	@if [ ! -d "$(REPO)/.git" ]; then \
		echo "Error: Not a Git repository: $(REPO)"; \
		exit 1; \
	fi
	devbox run -- uv run python -m src.cli.main serve $(REPO)

tail-logs:
	tail -f logs/api.log

test:
	devbox run -- uv run pytest -q tests/test_api.py

.PHONY: test-e2e
test-e2e:
	make install
	make api-start
	@echo "Waiting for API service to start..."
	@sleep 5
	make test
	make api-stop

actor-smoke:
	ACTOR_DEBUG=1 devbox run -- uv run python -m tools.mcp.actor_server.server --once '{"path": ".", "instruction": "echo hello"}'


setup-gemini:
	ln -s ./memory-bank/gemini/GEMINI.md ./GEMINI.md
