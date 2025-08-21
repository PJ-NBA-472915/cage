# Conventional Commits (No Scope)

## Overview
This rule enforces conventional commit message format without scope specification.

## Format
```
<type>: <description>

[optional body]

[optional footer(s)]
```

## Types
- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation only changes
- `style`: Changes that do not affect the meaning of the code (white-space, formatting, missing semi-colons, etc)
- `refactor`: A code change that neither fixes a bug nor adds a feature
- `perf`: A code change that improves performance
- `test`: Adding missing tests or correcting existing tests
- `chore`: Changes to the build process or auxiliary tools and libraries such as documentation generation
- `ci`: Changes to CI configuration files and scripts
- `build`: Changes that affect the build system or external dependencies
- `revert`: Reverts a previous commit

## Examples
✅ **Correct:**
- `feat: add user authentication system`
- `fix: resolve login validation issue`
- `docs: update api documentation`
- `refactor: simplify user model logic`
- `test: add unit tests for auth service`

❌ **Incorrect:**
- `feat(auth): add user authentication system` (has scope)
- `feat: add user authentication system` (missing space after colon)
- `FEAT: add user authentication system` (wrong case)
- `feat: Add user authentication system` (description starts with capital)
- `feat: add user authentication system and implement oauth` (multiple sentences)
- `feat: add User Authentication System` (contains uppercase)

## Rules
1. **No scope**: Do not include scope in parentheses
2. **Lowercase type**: Use lowercase for the commit type
3. **Space after colon**: Always include a space after the colon
4. **All lowercase**: Use lowercase for the entire commit message
5. **Single sentence**: Keep the description to one short sentence
6. **Imperative mood**: Use imperative mood ("add" not "added")
7. **No period**: Do not end description with a period
8. **Line length**: Keep the first line under 72 characters

## Enforcement
- All commit messages must follow this format
- Reject commits that don't conform to these rules
- Provide clear feedback on what needs to be corrected

## Task File Usage with Git Commits
When working with task files, follow this workflow:

### Before Committing
1. Update the task file with progress
2. Set `updated_at` to current timestamp
3. Update `progress_percent` based on completed To-Do items
4. Add entry to Changelog section

### Commit Message Format
Use the task ID and a brief description:
```
<type>: <task-id> <action>
```

### Examples
- `feat: 2025-08-21-refactor-auth-guards implement user authentication`
- `fix: 2025-08-21-refactor-auth-guards resolve login validation issue`
- `docs: 2025-08-21-refactor-auth-guards update task progress`
- `refactor: 2025-08-21-refactor-auth-guards simplify user model logic`

### Commit Workflow
```bash
# Update task file first
# Then commit with conventional format
git add .cursor/tasks/2025-08-21-taskname.md
git commit -m "feat: 2025-08-21-taskname <action description>"
```

### Rules for Task Commits
- Always reference the task ID in the commit message
- Keep the action description concise and lowercase
- Use appropriate commit type (feat, fix, docs, refactor, etc.)
- Commit task file changes before or with related code changes
