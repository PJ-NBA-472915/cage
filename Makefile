manage:
	devbox run -- python ./manage.py

tail-logs:
	devbox run -- tail -f logs/manage.log

## Initialise a repo
# Usage:
#   make init path=<path> [args="..."]
#   make init url=<url> [args="..."]
# Example:
#   make init url=https://github.com/some/repo.git args="--agent-id my-agent --branch main"
.PHONY: init
init:
ifndef path
ifndef url
	$(error Usage: make init path=<path> or url=<url>)
endif
endif
	$(if $(path), devbox run -- python3 manage.py repo init --origin $(path) $(args))
	$(if $(url), devbox run -- python3 manage.py repo init --origin $(url) $(args))
