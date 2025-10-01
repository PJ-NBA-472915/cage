# Backend Blueprint Crew Run

Objective: Coordinate agents to outline a feature flag service without touching the filesystem.

Prerequisites
- Access to cage crew endpoints.
- Fresh crew run (no prior artifacts persisted outside responses).

Steps
1. Create a crew with roles Architect, API Designer, and Project Manager; confirm the crew launch response.
2. Prompt Architect via crew endpoint for service overview, key components, data flow, and infrastructure assumptions.
3. Forward Architect output to API Designer; request REST or GraphQL endpoints, payload shapes, and error handling tied to the assumptions.
4. Forward both prior outputs to Project Manager; ask for milestones, tickets, and acceptance criteria linked to each endpoint.
5. End the session by exporting or storing the crew transcript through the platform tools only (no file writes).

Test Criteria
- Every artifact arrives as a crew response and cites assumptions from Step 2.
- API Designer plan covers each component mentioned by Architect.
- Project Manager backlog references endpoint names and includes acceptance criteria.
- Final transcript is available for later replay without any local file edits.
