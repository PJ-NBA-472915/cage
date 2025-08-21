---
id: "2025-08-21-agent-base-dockerfile"
title: "Agent Base Dockerfile (Fly-ready Ubuntu base for Agent Pods)"
owner: "Jaak"
status: "in-progress"
created_at: "2025-08-21 16:00"
updated_at: "2025-08-21 19:30"
progress_percent: 75
tags: ["cursor", "task", "docker", "fly.io", "agent"]
---

# Summary
Create a minimal, secure Ubuntu-based container image that ships with Python and the Gemini SDK configured for API access, includes the official Gemini CLI, accepts a runtime setup script for repo-specific tools, starts a lightweight daemon to manage agent pod lifecycle, and deploys cleanly on Fly.io with non-root user, health checks, and simple config.

# Success Criteria
- [x] Image builds locally and runs non-root under tini (PID 1)
- [x] If /app/pod-setup.sh exists, it runs on startup; otherwise start is not blocked
- [x] agent_daemon.py starts and logs a heartbeat every 10s
- [x] Presence/absence of GEMINI_API_KEY is handled: warn if missing, do not crash
- [ ] fly deploy works with provided fly.toml; health checks pass
- [x] Container size remains lean (base ≤ ~400–500MB uncompressed; no heavy extras by default)

# Acceptance Checks
- [x] Dockerfile builds successfully with Podman/Docker
- [x] Container runs as non-root user with tini as PID 1
- [x] Gemini CLI is available on PATH and responds to --version
- [x] Optional pod-setup.sh execution works correctly
- [x] Daemon starts and produces heartbeat logs
- [ ] Fly.io deployment succeeds with health checks passing
- [x] Base image size is within target range

# Subtasks
1. ✅ Base image & user setup (Ubuntu 24.04, Python, tini, non-root user)
2. ✅ LLM SDKs & dependencies (Python + Gemini CLI, Node.js ≥18)
3. ✅ Runtime bootstrap (pod-entrypoint.sh, pod-setup.sh handling)
4. ✅ Daemon implementation (agent_daemon.py with asyncio, heartbeat)
5. 🔄 Fly.io configuration (fly.toml, health checks, deployment)
6. 🔄 Validation & testing (local build, Fly deployment)

# To-Do
- [x] Create Dockerfile with Ubuntu 24.04 base
- [x] Install Python, pip, tini, curl, git, build-essential
- [x] Create non-root user and ensure /app is writable
- [x] Add requirements.txt with minimal Python dependencies
- [x] Install Node.js ≥18 and Gemini CLI globally
- [x] Write pod-entrypoint.sh for runtime setup handling
- [x] Create example pod-setup.sh for repo-specific tooling
- [x] Implement agent_daemon.py with Gemini init and heartbeat
- [x] Add fly.toml template with TCP health checks
- [x] Test local build with Podman/Docker
- [ ] Deploy to Fly.io and validate health checks
- [x] Document deployment workflow and environment variables

# Changelog
- 2025-08-21 19:45 — Created local network testing setup with docker-compose, router configuration, and test client scripts for validating inter-container communication before Fly.io deployment
- 2025-08-21 19:30 — Container successfully built and tested locally. All core functionality working including Gemini CLI, daemon heartbeat, and proper error handling for missing API key.
- 2025-08-21 16:00 — Task file created with comprehensive requirements and implementation plan

# Decisions & Rationale
- **Python vs Go for daemon**: Starting with Python for rapid delivery and richer LLM ecosystem; can revisit Go if performance bottlenecks appear
- **Base image approach**: Keep base minimal and push extras to pod-setup.sh to avoid bloat creep
- **Health checks**: Start with TCP checks for simplicity, can add HTTP /health endpoint later if needed
- **Ubuntu 24.04 Python handling**: Used virtual environment approach to handle externally managed Python environment restrictions

# Lessons Learned
- Initial task planning shows clear separation of concerns between base image and runtime customization
- Fly.io architecture requires careful consideration of process management and health monitoring
- Ubuntu 24.04 requires virtual environments for pip installations due to PEP 668 restrictions
- Virtual environment approach provides clean isolation and avoids system package conflicts
- **Container testing strategy**: Use background execution with `&` and then check logs/stop containers to avoid hanging terminal sessions
- **Long-running task handling**: When testing containers that run indefinitely, use `podman run --name container-name &` then `podman logs container-name` and `podman stop container-name` for clean testing workflow
- **Local-first approach**: Test all functionality locally before Fly.io deployment to catch issues early and validate the complete workflow

# Issues / Risks
- **Bloat creep**: Mitigation - Keep base minimal, push extras to pod-setup.sh ✅
- **Signal handling**: Mitigation - Use tini as PID 1, avoid bash as long-runner ✅
- **Credential leakage**: Mitigation - Use fly secrets for GEMINI_API_KEY, never bake keys into image ✅
- **Health checks failing**: Mitigation - Start with TCP check, add HTTP /health later if needed
- **Ubuntu 24.04 Python restrictions**: Mitigation - Use virtual environment for pip installations ✅

# Next Steps
1. ✅ Complete local testing and validation
2. 🔄 Test local network connectivity and inter-container communication
3. 🔄 Validate local agent pod networking and service discovery
4. 🔄 Test local health checks and monitoring
5. 🔄 Deploy to Fly.io for end-to-end validation (after local network testing)
6. 🔄 Final documentation updates and cleanup

# References
- [Fly.io Per-User Dev Environments Blueprint](https://fly.io/docs/blueprints/per-user-dev-environments/)
- [Fly.io Machines Documentation](https://fly.io/docs/machines/)
- [Google Generative AI Python SDK](https://ai.google.dev/docs/python_quickstart)
- [Gemini CLI Documentation](https://ai.google.dev/docs/gemini_cli)

# Deliverables
- [x] Dockerfile (Ubuntu 24.04, non-root, Python, Gemini SDK, tini, Node.js ≥18 LTS, Gemini CLI installed globally).
- [x] requirements.txt (minimal runtime deps for Python daemon).
- [x] pod-entrypoint.sh (executes optional pod-setup.sh, then daemon; verifies gemini --version on start).
- [x] agent_daemon.py (async skeleton; heartbeat; Gemini initialisation).
- [x] fly.toml template (TCP/HTTP health checks).
- [x] Example pod-setup.sh (repo-specific tooling hook).
- [x] README notes (env vars & deploy steps, Podman & Fly workflows).
- [x] docker-compose.local.yml (local network testing setup).
- [x] Local testing scripts (router-setup.sh, test-client-setup.sh, test-local-network.sh).
