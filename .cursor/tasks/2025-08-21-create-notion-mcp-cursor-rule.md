---
id: "2025-08-21-create-notion-mcp-cursor-rule"
title: "Create Cursor Rule File for Notion MCP Tool Interaction"
owner: "Jaak"
status: "done"
created_at: "2025-08-21 16:00"
updated_at: "2025-08-21 16:35"
progress_percent: 100
tags: ["cursor", "task", "notion", "mcp"]
---

# Summary
Create a cursor rule file that provides guidelines and best practices for interacting with the Notion MCP tool to access and manage the project board which is stored on the Project Tasks database on the PJ-NBA-472915 database in the General Notes database. This rule file will ensure consistent and effective usage of Notion MCP capabilities across the team.

Usage of this MCP will be managing and interacting with the project tasks board, and writing notes to the PJ-NBA-472915 Notes database.

# Process
When starting with a new task and writing the task file, the agent should:

1. **Divide the task into clear and atomic items** - Break down the main task into specific, trackable subtasks as Todo items
2. **Create project board entries** - For each Todo item, create a corresponding entry in the Project Tasks database on the PJ-NBA-472915 database
3. **Track progress through status updates**:
   - When a Todo item is started: Change the status property in the tasks board to "In Progress"
   - When a Todo item is completed: Change the status property in the tasks board to "Done"
4. **Maintain synchronization** - Keep the local task file Todo items and the Notion project board entries in sync throughout the task lifecycle

# Success Criteria
- [ ] Cursor rule file created with comprehensive Notion MCP interaction guidelines
- [ ] Rule file includes best practices for project board access and management
- [ ] Rule file provides examples of common Notion MCP operations
- [ ] Rule file is properly formatted and follows cursor rule conventions

# Acceptance Checks
- [ ] Rule file exists in the appropriate location
- [ ] Content covers Notion MCP tool usage comprehensively
- [ ] Examples are practical and relevant to project board management
- [ ] Format follows established cursor rule patterns
- [ ] Team can easily understand and follow the guidelines

# Subtasks
1. Research existing cursor rule patterns and Notion MCP tool capabilities
2. Define scope and structure of the rule file
3. Create comprehensive guidelines for Notion MCP interaction
4. Add practical examples and use cases
5. Review and refine the rule file content
6. Test rule file format and readability

# To-Do
- [x] Research cursor rule file patterns and structure
- [x] Investigate Notion MCP tool capabilities and limitations
- [x] Define the scope of guidelines needed
- [x] Create initial rule file structure
- [x] Write comprehensive Notion MCP interaction guidelines
- [x] Add practical examples for project board management
- [x] Include best practices and common pitfalls
- [x] Review and refine content for clarity
- [x] Test rule file format and readability
- [x] Finalize and commit the rule file

# Changelog
- 2025-08-21 16:35 — Committed completed task and new rule file to git repository.
- 2025-08-21 16:30 — Task completed successfully. Created comprehensive Notion MCP cursor rule file with guidelines, best practices, and examples.
- 2025-08-21 16:00 — File created.

# Decisions & Rationale
- Creating a dedicated rule file for Notion MCP interaction to ensure consistent usage across the team
- Focusing on project board access and management as the primary use case

# Lessons Learned
- Cursor rule files should follow established patterns with clear structure and comprehensive coverage
- Notion MCP tool provides extensive capabilities for project board and notes database management
- Integration between local task files and Notion project board requires careful synchronization planning
- Practical examples and troubleshooting sections are essential for team adoption

# Issues / Risks
- Need to understand the current Notion MCP tool capabilities
- May need to iterate on rule content based on team feedback

# Next Steps
- Team should review and provide feedback on the new rule file
- Consider adding specific examples based on actual project board usage
- Monitor rule effectiveness and update as needed based on team feedback

# References
- Notion MCP tool documentation
- Existing cursor rule patterns
- Project board requirements and workflows
