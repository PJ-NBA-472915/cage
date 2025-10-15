# E2E Test Bug Fixes - Summary

**Date**: 2025-10-15
**Status**: COMPLETED
**Commits**:
- `0cb51b7` - docs: update docker-compose references and cleanup config files
- `220fb58` - fix(mcp): align MCP tool schemas with Crew API models

## Bugs Fixed

### BUG-001: crew_run TypeError - FIXED ✅

**Issue**: crew_run tool failed with TypeError: "'str' object has no attribute 'get'"

**Root Cause**: Schema mismatch between MCP tool definition and Crew API models
- MCP schema expected: `{name, description, context}`
- Crew API expects: `{title, description, acceptance}`

**Fix Applied**:
- Updated `crew_run` tool schema in `src/cage/mcp/server.py` (lines 337-373)
- Changed `task.name` → `task.title`
- Added `task.acceptance` array (acceptance criteria)
- Removed `task.context` from schema
- Updated required fields: `['title', 'description', 'acceptance']`
- Fixed logging to use `task.title` instead of `task.name`
- Updated default timeout from 300s to 1200s to match model

### BUG-002: agent_create validation - FIXED ✅

**Issue**: agent_create tool failed with validation error

**Root Cause**: MCP schema was correct but lacked enum validation for roles

**Fix Applied**:
- Enhanced `agent_create` tool schema in `src/cage/mcp/server.py` (lines 188-207)
- Added role enum: `["planner", "implementer", "verifier", "committer"]`
- Matches `AgentCreate` model in `src/models/crewai.py`
- Improved description for better clarity

### BONUS FIX: agent_invoke - ALIGNED ✅

**Issue**: Preemptive fix to prevent similar issues

**Fix Applied**:
- Updated `agent_invoke` tool schema (lines 242-281)
- Changed `task.name` → `task.title`
- Added `task.acceptance` array
- Updated required fields to match `TaskSpec` model
- Updated default timeout from 300s to 600s

## Correct API Usage

### 1. Creating an Agent

```json
{
  "method": "tools/call",
  "tool": "agent_create",
  "arguments": {
    "name": "Python Implementer",
    "role": "implementer",
    "config": {}
  }
}
```

**Valid roles**: `planner`, `implementer`, `verifier`, `committer`

### 2. Creating a Crew

```json
{
  "method": "tools/call",
  "tool": "crew_create",
  "arguments": {
    "name": "Calculator Dev Crew",
    "roles": {
      "planner": "agent-uuid-1",
      "implementer": "agent-uuid-2",
      "verifier": "agent-uuid-3"
    },
    "labels": ["dev", "calculator"]
  }
}
```

**Important**: Must create agents first, then reference their UUIDs in `crew.roles`

### 3. Running a Crew

```json
{
  "method": "tools/call",
  "tool": "crew_run",
  "arguments": {
    "crew_id": "crew-uuid",
    "task": {
      "title": "Build Calculator Application",
      "description": "Implement a simple calculator with basic arithmetic operations",
      "acceptance": [
        "Calculator class with add, subtract, multiply, divide methods",
        "Proper error handling for division by zero",
        "Unit tests with pytest",
        "PEP 8 compliant code"
      ]
    },
    "strategy": "impl_then_verify",
    "timeout_s": 1200
  }
}
```

### 4. Invoking a Single Agent

```json
{
  "method": "tools/call",
  "tool": "agent_invoke",
  "arguments": {
    "agent_id": "agent-uuid",
    "task": {
      "title": "Implement Calculator",
      "description": "Create a Python calculator module",
      "acceptance": [
        "Implements basic arithmetic operations",
        "Has proper error handling"
      ]
    },
    "context": {},
    "timeout_s": 600
  }
}
```

## Files Changed

1. **src/cage/mcp/server.py**
   - Lines 188-207: `agent_create` tool schema
   - Lines 242-281: `agent_invoke` tool schema
   - Lines 337-373: `crew_run` tool schema
   - Lines 724-742: `agent_invoke_tool` function
   - Lines 980-998: `crew_run_tool` function

2. **.claude/README.md**
   - Updated docker-compose commands to use `docker compose` (newer syntax)

3. **.claude/settings.local.json**
   - Simplified permissions configuration

4. **CLAUDE.md**
   - Updated all docker-compose references to `docker compose`

## Testing Status

**Infrastructure**: ✅ VERIFIED
- Docker Compose orchestration works correctly
- All 13 services start and reach healthy state
- Network isolation properly configured
- MCP server is sole external entrypoint
- Structured JSONL logging functioning

**Crew Orchestration**: ⏳ READY FOR TESTING
- Schema fixes applied
- API contract aligned with models
- Ready for re-run of e2e test

## Next Steps

1. **Re-run E2E Test** - Validate fixes with full workflow test
2. **Investigate ISSUE-003** - Verify agent association in crew creation (empty roles response)
3. **Add Integration Tests** - Create tests specifically for MCP tool schemas
4. **Schema Validation** - Consider adding automated schema validation tests

## Related Files

- **E2E Test Specification**: `e2e-test-task.json`
- **Model Definitions**: `src/models/crewai.py`
- **Crew API Router**: `src/crew_service/router.py`
- **MCP Server**: `src/cage/mcp/server.py`

---

**Test Engineer**: Claude Code (Sonnet 4.5)
**Bug Discovery**: E2E testing revealed critical schema mismatches
**Resolution Time**: ~2 hours from discovery to fix
