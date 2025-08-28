PATH := /usr/local/bin:$(PATH)

manage:
	devbox run -- python ./manage.py

tail-logs:
	devbox run -- tail -f logs/manage.log

test:
	devbox run pytest

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
	$(if $(path), source .venv/bin/activate && python3 manage.py repo init --origin $(path) $(args))
	$(if $(url), source .venv/bin/activate && python3 manage.py repo init --origin $(url) $(args))

## Close a repo with optional merge
# Usage:
#   make repo-close REPO_PATH=<path> MESSAGE="<message>" [MERGE=1] [TARGET_BRANCH=<branch>] [args="..."]
# Example:
#   make repo-close REPO_PATH=/tmp/repo MESSAGE="finalise work" MERGE=1 TARGET_BRANCH=main
.PHONY: repo-close
repo-close:
ifndef REPO_PATH
	$(error Usage: make repo-close REPO_PATH=<path> MESSAGE="<message>" [MERGE=1] [TARGET_BRANCH=<branch>])
endif
ifndef MESSAGE
	$(error Usage: make repo-close REPO_PATH=<path> MESSAGE="<message>" [MERGE=1] [TARGET_BRANCH=<branch>])
endif
	source .venv/bin/activate && python3 manage.py repo close --path $(REPO_PATH) --message "$(MESSAGE)" $(if $(MERGE), --merge) $(if $(TARGET_BRANCH), --target-branch $(TARGET_BRANCH)) $(args)

.PHONY: manager
manager:
	source .venv/bin/activate && python3 manage.py manager
