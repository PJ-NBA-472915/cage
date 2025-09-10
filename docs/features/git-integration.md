# Feature: Git Integration

**Phase 3**

## 1. Overview

The Git Integration feature provides a set of tools to interact with a Git repository within the Cage environment. This feature is essential for creating an auditable trail of changes made by AI agents. It includes a set of Python functions for core Git operations and exposes these functions through a REST API.

All Git operations are designed to be used by the CrewAI agents to manage the codebase, from staging changes to creating commits and managing branches.

## 2. API Endpoints

The following REST API endpoints are provided for interacting with the Git repository:

*   `GET /git/status`: Get the status of the repository, including modified, new, and untracked files.
*   `POST /git/branch`: Create a new branch.
*   `POST /git/commit`: Create a new commit.
*   `POST /git/push`: Push changes to a remote repository.
*   `POST /git/pull`: Pull changes from a remote repository.
*   `POST /git/merge`: Merge branches.

### 2.1 `GET /git/status`

**Request:**

```
GET /git/status
```

**Response:**

```json
{
  "status": "..."
}
```

### 2.2 `POST /git/commit`

**Request:**

```json
{
  "message": "Your commit message"
}
```

**Response:**

```json
{
  "sha": "commit_sha",
  "message": "Your commit message",
  "author": "...",
  "date": "..."
}
```

## 3. Usage

The Git integration is designed to be used as part of an automated workflow orchestrated by CrewAI.

**Example Workflow:**

1.  An AI agent uses the **Editor Tool** to make changes to a file.
2.  The agent calls `POST /files/edit` to stage the changes.
3.  The agent calls `POST /git/commit` with a descriptive message to commit the changes.
4.  The commit is recorded in the `task.provenance` for the current task.

## 4. Commit Provenance

Every commit made through the Git integration is tracked in the `provenance` section of the corresponding task file. This creates a permanent and auditable record of all changes.

The `provenance.commits` array in the task JSON file will contain an entry for each commit with the following information:

*   `sha`: The Git commit SHA.
*   `title`: The commit message.
*   `files_changed`: A list of files that were modified in the commit.
*   `insertions`: The number of lines added.
*   `deletions`: The number of lines removed.

**Example `task.json` snippet:**

```json
"provenance": {
  "commits": [
    {
      "sha": "a1b2c3d4",
      "title": "feat: Implement user authentication",
      "files_changed": ["src/api/auth.py", "tests/test_auth.py"],
      "insertions": 50,
      "deletions": 5
    }
  ]
}
```

## 5. Integration with Editor Tool

The Git integration is tightly coupled with the Editor Tool. When the Editor Tool is used to modify a file, the changes are automatically staged for the next commit. This ensures that all changes made by AI agents are properly versioned and tracked.
