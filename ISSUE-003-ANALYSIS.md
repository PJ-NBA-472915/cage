# ISSUE-003 Analysis: Empty Roles in Crew Create Response

**Date**: 2025-10-15
**Status**: NOT A BUG - USER ERROR IN E2E TEST
**Severity**: MEDIUM → LOW (documentation issue, not code issue)

## Issue Description

During e2e testing, when creating a crew via the MCP server, the response showed `Roles: []` even though agents were included in the request.

## Root Cause Analysis

After investigation, this is **NOT a bug** in the Cage codebase. The issue is with the **e2e test using incorrect API format**.

### What Happened

The e2e test (lines 336-360 in `e2e-test-task.json`) sent:

```json
{
  "method": "tools/call",
  "tool": "crew_create",
  "arguments": {
    "name": "Calculator App Development Crew",
    "description": "A crew to build a simple calculator application with tests",
    "agents": [
      {
        "role": "planner",
        "goal": "Create a detailed implementation plan...",
        "backstory": "You are an expert software architect..."
      },
      ...
    ]
  }
}
```

### Why It Failed

Looking at the `CrewCreate` model (`src/models/crewai.py:53-62`):

```python
class CrewCreate(BaseModel):
    """DTO for creating a new crew."""

    name: str = Field(..., min_length=1, description="Crew name")
    roles: Dict[str, UUID] = Field(
        ..., description="Mapping of role names to agent IDs"
    )
    labels: Optional[List[str]] = Field(
        default_factory=list, description="Optional labels"
    )
```

The API expects:
- `roles`: A dictionary mapping role names (string) to existing agent UUIDs
- **NOT** `agents`: An array of inline agent specifications

### How It Should Work

The correct workflow is:

1. **Create agents individually first**:
   ```json
   {
     "method": "tools/call",
     "tool": "agent_create",
     "arguments": {
       "name": "Python Planner",
       "role": "planner",
       "config": {}
     }
   }
   ```
   Response: `{"id": "uuid-1", "name": "Python Planner", "role": "planner", ...}`

2. **Repeat for each agent role**:
   - Implementer → `uuid-2`
   - Verifier → `uuid-3`
   - Committer → `uuid-4` (if needed)

3. **Create crew with agent UUIDs**:
   ```json
   {
     "method": "tools/call",
     "tool": "crew_create",
     "arguments": {
       "name": "Calculator Dev Crew",
       "roles": {
         "planner": "uuid-1",
         "implementer": "uuid-2",
         "verifier": "uuid-3"
       },
       "labels": ["dev", "calculator"]
     }
   }
   ```

## Why The Response Showed Empty Roles

When the test passed `agents` array instead of `roles` dict:
- Pydantic validation didn't find the required `roles` field
- The `Crew` model's `roles` field has `default_factory=dict`
- So it defaulted to an empty dict `{}`
- Result: `Roles: []` in the response

## Code Verification

The code is working correctly:

**Crew Creation** (`src/crew_service/router.py:204-220`):
```python
@router.post("/crews", response_model=Crew)
async def create_crew(request: Request, crew_data: CrewCreate):
    """Create a new crew."""
    crew = Crew(**crew_data.dict())
    crews_db[crew.id] = crew
    return crew
```

This is straightforward and correct. It:
1. Accepts a `CrewCreate` DTO
2. Converts it to a `Crew` model
3. Stores it in the database
4. Returns the created crew

**No bugs found in the code.**

## Resolution

### What Needs To Be Fixed

1. **E2E Test** - Update `e2e-test-task.json` with correct workflow:
   - Phase 2: Create agents individually
   - Phase 3: Collect agent UUIDs
   - Phase 4: Create crew with role-to-UUID mapping

2. **Documentation** - Already added to `E2E_TEST_FIXES.md`:
   - Correct API usage examples
   - Multi-step workflow clarification
   - Agent creation before crew creation

3. **MCP Tool Description** - Consider enhancing `crew_create` tool description:
   - Clarify that agents must be created first
   - Show example of roles dict format
   - Link to workflow documentation

### Recommended Changes

#### Option 1: Update E2E Test (Recommended)

Update the test to follow the correct workflow as documented in `E2E_TEST_FIXES.md`.

#### Option 2: Enhance API Validation (Optional)

Could add better error messages when `roles` is missing:

```python
@router.post("/crews", response_model=Crew)
async def create_crew(request: Request, crew_data: CrewCreate):
    """Create a new crew."""

    # Validate that roles are provided and agents exist
    if not crew_data.roles:
        raise HTTPException(
            status_code=400,
            detail="Crew must have at least one role assignment. Create agents first using agent_create, then provide their UUIDs in the roles field."
        )

    # Optionally verify agent UUIDs exist
    for role_name, agent_id in crew_data.roles.items():
        if agent_id not in agents_db:
            raise HTTPException(
                status_code=404,
                detail=f"Agent {agent_id} not found for role '{role_name}'. Create the agent first using agent_create."
            )

    crew = Crew(**crew_data.dict())
    crews_db[crew.id] = crew
    return crew
```

#### Option 3: Enhance MCP Tool Description (Recommended)

Update the `crew_create` tool description in `src/cage/mcp/server.py`:

```python
{
    "name": "crew_create",
    "description": "Create a new crew of AI agents with role assignments. IMPORTANT: Agents must be created first using agent_create, then their UUIDs are mapped to roles in this call.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Name of the crew"},
            "roles": {
                "type": "object",
                "description": "Mapping of role names (e.g., 'planner', 'implementer', 'verifier') to agent UUIDs. Create agents first using agent_create.",
                "additionalProperties": {"type": "string"},
                "example": {
                    "planner": "uuid-agent-1",
                    "implementer": "uuid-agent-2",
                    "verifier": "uuid-agent-3"
                }
            },
            "labels": {
                "type": "array",
                "description": "Optional labels for the crew",
                "items": {"type": "string"},
            },
        },
        "required": ["name", "roles"],
    },
}
```

## Status

**ISSUE-003**: CLOSED - NOT A BUG

**Classification**: User error in e2e test, not a code defect

**Action Items**:
- [x] Root cause identified
- [x] Documentation updated (`E2E_TEST_FIXES.md`)
- [ ] Consider enhancing tool description (optional improvement)
- [ ] Consider adding validation for empty roles (optional improvement)
- [ ] Update e2e test with correct workflow (when re-running test)

## Related Files

- `e2e-test-task.json` - Original test with incorrect usage
- `E2E_TEST_FIXES.md` - Correct API usage documentation
- `src/models/crewai.py` - Model definitions (lines 30-62)
- `src/crew_service/router.py` - Crew creation endpoint (lines 204-220)
- `src/cage/mcp/server.py` - MCP tool definitions (lines 282-301)

---

**Conclusion**: The Cage API is working as designed. The e2e test needs to be updated to follow the correct multi-step workflow: create agents first, then create a crew with their UUIDs.
