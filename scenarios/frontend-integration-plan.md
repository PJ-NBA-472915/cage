# Frontend Integration Plan Crew Run

Objective: Guide agents to create a React integration plan against a provided API spec using only crew interactions.

Prerequisites
- Access to cage crew endpoints.
- API spec text ready to paste into crew prompts.

Steps
1. Launch a crew with UI Lead, UX Writer, and QA Analyst; confirm crew identifiers.
2. Send the API spec text to the UI Lead; request routing structure, state management choice, and component list covering every endpoint.
3. Pass UI Lead output to the UX Writer; ask for UX copy guidelines and interaction notes mapped to each component.
4. Share both prior outputs with the QA Analyst; request manual test scripts, edge-case checks, and automation candidates linked to components.
5. Close the crew run after capturing all responses through the platform; avoid creating or editing any local files.

Test Criteria
- UI Lead plan references all endpoints from the supplied spec.
- UX Writer output covers every user-facing state listed by UI Lead.
- QA Analyst scripts include happy path, boundary, and failure scenarios per component.
- All deliverables exist only in crew responses; no filesystem changes occur.
