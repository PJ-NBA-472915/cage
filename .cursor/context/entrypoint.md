# .cursor/context Directory Guide

This directory contains contextual information and documentation that helps Cursor AI understand the project structure, requirements, and conventions. This guide explains what's stored here and how to use it effectively.

## Directory Structure

```
.cursor/context/
├── entrypoint.md                    # This file - the main guide
├── product/                         # Product specifications and requirements
│   └── specification-document.md    # Distributed task system specification
└── [future directories]             # Additional context categories
```

## What's Stored Here

### Product Context (`product/`)

The `product/` subdirectory contains high-level product specifications, requirements, and design documents that help Cursor understand:

- **Project goals and scope** - What the system is trying to achieve
- **Technical requirements** - Functional and non-functional requirements
- **Architecture decisions** - Design choices and trade-offs
- **User stories and use cases** - How the system will be used
- **Success criteria** - How to measure if the implementation is correct

### Current Documents

#### `specification-document.md`
- **Purpose**: Defines a containerised, distributed task system
- **Key Components**: Coordinator service, Agent workers, Redis queueing, Postgres persistence, Observability stack
- **Status**: Draft (v0.1)
- **Use Case**: Reference for implementing the core system architecture

## How to Access This Information

### For Cursor AI
Cursor automatically reads and considers the contents of this directory when:
- Understanding project context
- Making architectural decisions
- Implementing features
- Writing code that aligns with project goals

### For Developers
- **Read the specs**: Understand what you're building before coding
- **Reference during development**: Check requirements and design decisions
- **Update as needed**: Keep specifications current with implementation

## How to Use This Context

### 1. **Before Starting Development**
- Read the relevant specification documents
- Understand the success criteria and requirements
- Review the architecture and design decisions

### 2. **During Implementation**
- Reference the specifications to ensure alignment
- Use the documented requirements as acceptance criteria
- Follow the established patterns and conventions

### 3. **When Making Decisions**
- Check if your approach aligns with documented goals
- Consider the trade-offs already documented
- Update specifications if you discover new requirements

### 4. **For Code Reviews**
- Use specifications as a basis for review criteria
- Ensure implementations meet documented requirements
- Flag deviations from the established architecture

## Best Practices

### Keep Context Updated
- Update specifications when requirements change
- Document new decisions and trade-offs
- Maintain consistency between docs and implementation

### Use Clear Language
- Write specifications that both technical and non-technical stakeholders can understand
- Include concrete examples and use cases
- Define success criteria that can be measured

### Organize by Category
- Group related context into logical subdirectories
- Use consistent naming conventions
- Keep the entrypoint file current with the directory structure

## Adding New Context

When adding new context files:

1. **Choose the right category**: Place files in appropriate subdirectories
2. **Update this entrypoint**: Add new files to the directory structure
3. **Follow naming conventions**: Use descriptive, lowercase filenames with hyphens
4. **Link related documents**: Reference other relevant context files

### Example New Context
```
.cursor/context/
├── entrypoint.md
├── product/
│   ├── specification-document.md
│   └── api-design.md              # New API design document
├── technical/                      # New technical context category
│   ├── deployment-guide.md        # Deployment procedures
│   └── testing-strategy.md        # Testing approach
└── team/                          # Team and process context
    └── coding-standards.md        # Development standards
```

## Current Project Context

Based on the existing specification, this project is building:

- A **distributed task processing system** with Coordinator and Agent components
- **Redis-based task queueing** for reliable job distribution
- **Postgres persistence** for task lifecycle management
- **Observability stack** (Prometheus, Loki, Grafana) for monitoring
- **Containerised deployment** with Docker and Fly.io

The system aims to handle 1000+ tasks per minute reliably while providing end-to-end visibility and fault tolerance.

## Getting Help

If you need to:
- **Understand a requirement**: Read the relevant specification document
- **Make an architectural decision**: Check documented trade-offs and decisions
- **Add new context**: Follow the organization patterns established here
- **Update existing context**: Ensure consistency with other documents

Remember: This context directory is a living document. Keep it current, clear, and useful for both humans and AI assistants.
