---
description: Comprehensive guidelines for interacting with the Notion MCP tool to manage project boards and notes databases. Ensures consistent and effective usage across the team.
globs:
  - "**/*"
alwaysApply: true
---

# Notion MCP Tool Interaction Guidelines

## Overview
This rule provides comprehensive guidelines and best practices for interacting with the Notion MCP tool to access and manage the project board stored in the Project Tasks database on the PJ-NBA-472915 database in the General Notes database. It ensures consistent and effective usage of Notion MCP capabilities across the team.

## Primary Use Cases
1. **Project Board Management**: Creating, updating, and tracking project tasks
2. **Notes Database**: Writing and managing notes in the PJ-NBA-472915 Notes database
3. **Task Synchronization**: Keeping local task files and Notion project board entries in sync

## Notion MCP Tool Capabilities

### Available Functions
- `mcp_Notion_search`: Search across Notion workspace and connected sources
- `mcp_Notion_fetch`: Retrieve details about Notion pages and databases
- `mcp_Notion_notion-create-pages`: Create new pages with specified properties and content
- `mcp_Notion_notion-update-page`: Update page properties or content
- `mcp_Notion_notion-move-pages`: Move pages to new parent locations
- `mcp_Notion_notion-duplicate-page`: Duplicate existing pages
- `mcp_Notion_notion-create-database`: Create new databases with custom schemas
- `mcp_Notion_notion-update-database`: Update database properties and structure
- `mcp_Notion_notion-create-comment`: Add comments to pages
- `mcp_Notion_notion-get-comments`: Retrieve page comments
- `mcp_Notion_notion-get-users`: List workspace users
- `mcp_Notion_notion-get-self`: Retrieve bot user information

## Project Board Management Workflow

### 1. Task Creation Process
When creating a new task in the project board:

```markdown
# Required Properties
- **Task Name**: Clear, descriptive title
- **Status**: "Not Started", "In Progress", "Review", "Done", "Blocked"
- **Priority**: "Low", "Medium", "High", "Critical"
- **Assigned To**: Team member responsible
- **Due Date**: Target completion date
- **Description**: Detailed task requirements and context
```

### 2. Task Status Updates
- **Not Started**: Initial state for new tasks
- **In Progress**: Task is actively being worked on
- **Review**: Task completed, awaiting review/approval
- **Done**: Task successfully completed
- **Blocked**: Task cannot proceed due to external dependencies

### 3. Task Synchronization
Maintain consistency between local task files and Notion project board:
- Update Notion status when local task status changes
- Sync progress percentages between systems
- Keep task descriptions and requirements aligned

## Notes Database Usage

### Content Guidelines
- Use clear, structured formatting with headers and bullet points
- Include relevant context and background information
- Tag content appropriately for easy discovery
- Maintain consistent formatting across similar note types

### Common Note Types
- **Meeting Notes**: Structured with agenda, attendees, decisions, and action items
- **Technical Documentation**: Code examples, architecture decisions, implementation details
- **Project Updates**: Progress reports, milestone achievements, blocker identification
- **Process Documentation**: Workflows, procedures, and best practices

## Best Practices

### 1. Search and Discovery
- Use semantic search for finding relevant content
- Leverage database-specific searches for targeted results
- Combine search terms for more precise results

### 2. Content Creation
- Always include a descriptive title
- Use consistent formatting and structure
- Include relevant metadata and tags
- Link related content when appropriate

### 3. Database Management
- Respect existing database schemas
- Use consistent property values
- Maintain data integrity and relationships
- Follow naming conventions for new properties

### 4. Error Handling
- Handle API rate limits gracefully
- Provide clear error messages for failed operations
- Implement retry logic for transient failures
- Log errors for debugging and monitoring

## Common Operations

### Creating a Project Task
```markdown
1. Use `mcp_Notion_notion-create-pages` with parent database ID
2. Set required properties (Task Name, Status, Priority, etc.)
3. Include detailed description in content
4. Set appropriate due dates and assignments
```

### Updating Task Status
```markdown
1. Fetch current page using `mcp_Notion_notion-fetch`
2. Use `mcp_Notion_notion-update-page` to modify status
3. Update related properties as needed
4. Add status change comment if required
```

### Adding Notes
```markdown
1. Create new page in Notes database
2. Use structured content with clear headers
3. Include relevant metadata and tags
4. Link to related project tasks when applicable
```

## Integration with Task Files

### Synchronization Points
- **Task Creation**: Create Notion entry when local task file is created
- **Status Changes**: Update Notion status when local status changes
- **Progress Updates**: Sync progress percentages between systems
- **Completion**: Mark Notion task as "Done" when local task completes

### Required Properties Mapping
| Local Task Field | Notion Property | Notes |
|------------------|-----------------|-------|
| Status | Status | Map local status to Notion status values |
| Progress | Progress | Convert percentage to Notion format |
| Due Date | Due Date | Ensure date format compatibility |
| Description | Description | Sync content between systems |

## Troubleshooting

### Common Issues
1. **Authentication Errors**: Verify MCP token configuration
2. **Rate Limiting**: Implement exponential backoff for retries
3. **Schema Mismatches**: Validate property names and types
4. **Permission Errors**: Check workspace access and page permissions

### Debugging Steps
1. Verify MCP server configuration
2. Check authentication token validity
3. Validate database and page IDs
4. Review API response for error details
5. Check workspace permissions and access

## Security Considerations

### Data Protection
- Never log sensitive information
- Use environment variables for configuration
- Implement proper access controls
- Regular security audits of MCP usage

### Access Management
- Limit MCP access to necessary functions
- Monitor usage patterns for anomalies
- Implement user authentication where possible
- Regular review of access permissions

## Performance Optimization

### Efficient Operations
- Batch operations when possible
- Use targeted searches instead of broad queries
- Cache frequently accessed data
- Implement connection pooling for multiple requests

### Monitoring
- Track API response times
- Monitor rate limit usage
- Log performance metrics
- Set up alerts for performance degradation

## Examples

### Example 1: Creating a New Project Task
```markdown
Task: Implement user authentication system
Status: Not Started
Priority: High
Assigned To: Development Team
Due Date: 2025-09-15
Description: Build secure user authentication with OAuth2 support
```

### Example 2: Updating Task Progress
```markdown
Current Status: In Progress
Progress: 60%
Updated Description: Core authentication logic implemented, OAuth2 integration in progress
Next Steps: Complete OAuth2 integration and add unit tests
```

### Example 3: Adding Meeting Notes
```markdown
Meeting: Sprint Planning - Week 3
Date: 2025-08-21
Attendees: Development Team, Product Manager
Decisions: Implement authentication system, prioritize security features
Action Items: Research OAuth2 providers, design user flow, create test plan
```

## Maintenance and Updates

### Regular Reviews
- Monthly review of rule effectiveness
- Quarterly updates based on team feedback
- Annual comprehensive revision
- Continuous improvement based on usage patterns

### Version Control
- Track rule changes in version control
- Document major updates and rationale
- Maintain change log for transparency
- Coordinate updates with team training

## References
- [Notion API Documentation](https://developers.notion.com/)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [Project Board Schema Documentation](internal)
- [Team Workflow Guidelines](internal)
