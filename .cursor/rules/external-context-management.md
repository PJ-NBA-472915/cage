# External Context Management Rule

## Overview
This rule governs how Cursor should interact with the `.cursor/context/` directory to maintain project knowledge and retrieve relevant information throughout discussions and tasks.

## Core Principles

### 1. **Always Start with Entrypoint**
- **At the beginning of each discussion**, Cursor MUST read `.cursor/context/entrypoint.md`
- This file serves as the central index and guide to all available context
- Use the entrypoint to understand what context categories and files exist

### 2. **Selective Context Retrieval**
- **Do NOT fetch all context files automatically**
- Only retrieve context files that are directly relevant to the current task or discussion
- Use the entrypoint.md to identify which files might be relevant
- Leave out context files that are not pertinent to avoid information overload

### 3. **Dynamic Context Discovery**
- **Throughout the discussion**, if new topics emerge that require additional context:
  - Identify which context files might contain relevant information
  - Fetch those specific files as needed
  - Don't wait for the user to explicitly request context retrieval

### 4. **Context Preservation and Updates**
- **When valuable information emerges** during discussions:
  - Store it in the appropriate context directory
  - Update the `entrypoint.md` file to reflect new information
  - Maintain the context directory as a living knowledge base

## Implementation Workflow

### Phase 1: Initial Context Loading
1. **Read entrypoint.md** - Always start here
2. **Analyze current task** - Understand what the user is asking for
3. **Identify relevant context** - Based on entrypoint.md and task requirements
4. **Fetch only relevant files** - Retrieve context that directly supports the current work

### Phase 2: Dynamic Context Management
1. **Monitor discussion flow** - Pay attention to emerging topics
2. **Assess context needs** - Determine if additional context would be helpful
3. **Fetch on-demand** - Retrieve relevant context files as topics evolve
4. **Maintain focus** - Don't fetch context that's not immediately relevant

### Phase 3: Context Preservation
1. **Capture insights** - When valuable information emerges during discussions
2. **Categorize appropriately** - Place information in the right context subdirectory
3. **Update entrypoint.md** - Keep the central index current
4. **Maintain consistency** - Ensure new context aligns with existing structure

## Context Categories and Organization

### Product Context (`product/`)
- Product specifications, requirements, and design documents
- User stories, use cases, and success criteria
- Architecture decisions and trade-offs

### Technical Context (`technical/`)
- Implementation details, patterns, and conventions
- Deployment procedures and infrastructure
- Testing strategies and quality assurance

### Team Context (`team/`)
- Development standards and coding conventions
- Process workflows and collaboration practices
- Knowledge sharing and documentation practices

### Project Context (`project/`)
- Current status, milestones, and progress
- Known issues and technical debt
- Future roadmap and planning

## Best Practices

### Context Retrieval
- **Be selective** - Only fetch what's immediately relevant
- **Be proactive** - Anticipate context needs based on discussion direction
- **Be efficient** - Don't re-fetch context that's already loaded
- **Be focused** - Avoid context that distracts from the current task

### Context Storage
- **Be organized** - Use consistent naming and directory structure
- **Be descriptive** - Write clear, searchable content
- **Be current** - Update context when information changes
- **Be linked** - Reference related context files when appropriate

### Context Maintenance
- **Regular updates** - Keep entrypoint.md current with directory structure
- **Quality control** - Ensure stored context is accurate and useful
- **Cleanup** - Remove outdated or incorrect context
- **Validation** - Verify that stored context aligns with current project state

## Examples

### Example 1: Starting a New Discussion
```
User: "I need help implementing the task queue system"
Cursor: [Reads entrypoint.md] → [Identifies product/specification-document.md as relevant] → [Fetches only that file] → [Proceeds with implementation help]
```

### Example 2: Context Emergence During Discussion
```
User: "Actually, I'm also thinking about deployment"
Cursor: [Recognizes deployment context needed] → [Checks entrypoint.md for deployment-related files] → [Fetches technical/deployment-guide.md if it exists] → [Continues discussion with deployment context]
```

### Example 3: Capturing New Knowledge
```
User: "We decided to use Redis Cluster instead of single Redis for better scalability"
Cursor: [Recognizes architectural decision] → [Stores in product/architecture-decisions.md] → [Updates entrypoint.md to reference new file] → [Maintains knowledge for future discussions]
```

## Compliance Requirements

- **MUST** read entrypoint.md at the start of every discussion
- **MUST** only fetch context files that are directly relevant
- **MUST** dynamically retrieve additional context as topics evolve
- **MUST** store valuable new information in appropriate context files
- **MUST** keep entrypoint.md updated with new context additions
- **MUST NOT** fetch all context files automatically
- **MUST NOT** ignore the need for additional context during discussions

## Success Metrics

- Context retrieval is targeted and relevant
- New knowledge is consistently captured and organized
- Entrypoint.md remains current and useful
- Context directory grows as a valuable knowledge base
- Discussions are informed by appropriate context without information overload
