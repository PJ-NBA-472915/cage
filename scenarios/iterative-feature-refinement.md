# Iterative Feature Refinement Crew Run

Objective: Exercise multi-round collaboration on a payments dashboard concept strictly through crew exchanges.

Prerequisites
- Access to cage crew endpoints.
- Initial feature description text ready for agent prompts.

Steps
1. Start a crew with Product Strategist, Tech Lead, and Reviewer roles; record crew identifiers from the response.
2. Round 1: Provide the feature concept to Product Strategist; request feature goals, user stories, and KPIs returned in a single response.
3. Round 2: Deliver Strategist output to Tech Lead; ask for feasibility notes, system impact summary, and revised user stories.
4. Round 3: Send both prior rounds to Reviewer; request inconsistency checks, risk list, and a go/no-go recommendation with open questions.
5. (Optional) If open questions remain, spawn an Analyst via crew endpoints to resolve them, sharing all relevant transcripts.
6. Conclude the run once Reviewer (or Analyst) issues final guidance; do not save files locally.

Test Criteria
- Each round explicitly references the outputs it reviewed.
- Reviewer disposition resolves or tracks every open issue.
- Optional Analyst conclusions align with the previous round notes (if used).
- Audit trail shows ordered crew interactions with no filesystem modifications.
