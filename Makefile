PATH := /usr/local/bin:$(PATH)

.PHONY: install
install:
	devbox run -- uv pip install -r requirements.txt

.PHONY: api-start
api-start:
	devbox run -- python ./manage.py start

.PHONY: api-stop
api-stop:
	devbox run -- python ./manage.py stop

.PHONY: api-status
api-status:
	devbox run -- python ./manage.py status

tail-logs:
	devbox run -- tail -f logs/api.log

test:
	devbox run -- pytest -q tests/test_api.py

.PHONY: test-e2e
test-e2e:
	make install
	make api-start
	@echo "Waiting for API service to start..."
	@sleep 5
	make test
	make api-stop

actor-smoke:
	ACTOR_DEBUG=1 devbox run python -m tools.mcp.actor_server.server --once '{"path": ".", "instruction": "echo hello"}'


setup-gemini:
	ln -s ./memory-bank/gemini/GEMINI.md ./GEMINI.md
