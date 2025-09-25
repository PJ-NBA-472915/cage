# 🚀 Cage API Postman Collection Guide

## Overview

This comprehensive Postman collection provides complete coverage of the Cage Pod Multi-Agent Repository Service API, with special focus on **individual agent testing** - the key feature for reducing feedback loops during development.

## 🎯 Key Features

### ✨ Individual Agent Testing (NEW!)
- **Test agents separately** without running full crew
- **Reduce feedback loops** and development time
- **Isolate issues** to specific agents
- **Rapid iteration** on agent configurations

### 📋 Complete API Coverage
- **35+ endpoints** across all Cage API features
- **Auto-generated variables** for seamless testing
- **Comprehensive test scripts** with validation
- **Rich documentation** for every endpoint

## 🚀 Quick Start

### 1. Import Collection
1. Download `postman_collection.json`
2. Import into Postman
3. Collection will appear as "Cage Pod API - Complete Collection"

### 2. Set Environment Variables
Create a Postman environment with these variables:

```
base_url: http://localhost:8000
pod_token: dev-token
```

**Note**: Variables are auto-generated if not set, but you should configure them for your environment.

### 3. Start Testing Individual Agents
1. Go to "🤖 Individual Agents (NEW!)" folder
2. Run "List Available Agents" to see all agents
3. Use individual agent test requests to test each agent separately

## 🤖 Individual Agent Testing

### Available Agents
- **planner**: Creates detailed execution plans using Cage-native API endpoints
- **implementer**: Executes file operations and code changes using Editor Tool
- **reviewer**: Reviews changes for quality and compliance
- **committer**: Handles Git operations and commits using Git Tool

### Testing Workflow
1. **List Available Agents** - See all registered agents
2. **Test Individual Agent - [Type]** - Test specific agent with realistic scenarios
3. **Get Agent Info** - Get detailed configuration for any agent

### Example Individual Agent Tests
```json
// Test Planner Agent
{
    "agent": "planner",
    "request": "Create a detailed plan for building a user authentication system"
}

// Test Implementer Agent
{
    "agent": "implementer", 
    "request": "Create a Python file called 'auth.py' with a login function"
}

// Test Reviewer Agent
{
    "agent": "reviewer",
    "request": "Review the authentication code for security vulnerabilities"
}

// Test Committer Agent
{
    "agent": "committer",
    "request": "Create a Git commit for the authentication system changes"
}
```

## 📁 Collection Structure

### 🏥 System Health
- Health Check (no auth required)
- About (pod information)

### 🤖 Individual Agents (NEW!)
- List Available Agents
- Test Individual Agent - Planner
- Test Individual Agent - Implementer  
- Test Individual Agent - Reviewer
- Test Individual Agent - Committer
- Get Agent Info

### 📋 Task Management
- Create Task (with auto-generated ID)
- Get Task
- List Tasks
- Update Task

### 📁 File Operations
- Create File (INSERT operation)
- Read File (GET operation)
- Get File SHA (validation)

### 🔀 Git Operations
- Git Status
- List Branches
- Create Branch (with timestamp)
- Commit Changes (conventional format)
- Git History

### 🧠 RAG System
- RAG Query (requires OPENAI_API_KEY)
- RAG Reindex

### 👥 Crew Operations
- Create Crew Plan (traditional workflow)
- Apply Crew Plan (full crew execution)

### 🔧 Utilities
- Rebuild Task Tracker
- Execute Command
- Get Diff

## 🔧 Auto-Generated Variables

The collection automatically generates these variables:

- **task_id**: `YYYY-MM-DD-test-XXX` format
- **agent_name**: Defaults to "planner", updated from agent list
- **timestamp**: Current timestamp for unique operations
- **test_branch**: `postman-test-{timestamp}` for branch creation

## 📝 Test Scripts

Every request includes comprehensive test scripts:

### Global Tests (all requests)
- Response time validation (< 30 seconds)
- HTTP status code validation
- JSON response validation
- Error handling and logging

### Endpoint-Specific Tests
- Success criteria validation
- Response structure verification
- Data extraction for chaining requests
- Agent-specific validation

## 🎯 Usage Scenarios

### 1. Individual Agent Development
```
1. Run "List Available Agents"
2. Test specific agent with "Test Individual Agent - [Type]"
3. Iterate on agent configuration
4. Repeat testing without full crew overhead
```

### 2. API Exploration
```
1. Start with "Health Check"
2. Explore each folder systematically
3. Use auto-generated variables
4. Review test results and logs
```

### 3. Integration Testing
```
1. Create Task
2. Test individual agents
3. Create files via File Operations
4. Commit via Git Operations
5. Validate end-to-end workflow
```

### 4. Development Debugging
```
1. Use individual agent testing to isolate issues
2. Check specific agent configuration with "Get Agent Info"
3. Use utility endpoints for system state
4. Review logs and responses for troubleshooting
```

## 🔐 Authentication

All endpoints (except Health Check and About) require authentication:

```
Authorization: Bearer {{pod_token}}
```

The collection automatically handles this via collection-level auth configuration.

## ⚠️ Important Notes

### RAG System
- RAG endpoints require `OPENAI_API_KEY` environment variable
- Returns 503 if not configured (this is expected)
- Test scripts handle this gracefully

### Individual Agent Testing
- **This is the key feature** for reducing feedback loops
- Much faster than full crew execution
- Perfect for development and debugging
- Allows focused testing of specific agent behaviors

### File Operations
- Creates test files in repository root
- Uses correlation IDs for tracking
- Includes proper intent descriptions
- Supports dry-run mode for testing

### Git Operations
- Follows conventional commit message format
- Includes task ID references
- Auto-generates unique branch names
- Provides comprehensive status information

## 🚀 Best Practices

### 1. Start with Individual Agents
- Always test individual agents first
- Use full crew only when needed
- Iterate quickly with individual testing

### 2. Use Environment Variables
- Set up proper environment for your setup
- Use meaningful task IDs and correlation IDs
- Keep tokens secure

### 3. Review Test Results
- Check console logs for detailed information
- Validate response structures
- Use test results to guide development

### 4. Chain Requests
- Use variables to chain related requests
- Build workflows with multiple endpoints
- Leverage auto-generated IDs

## 🔄 Version History

- **v2.0**: Complete rewrite with individual agent testing
- **v1.0**: Basic collection with limited endpoints

## 🆘 Troubleshooting

### Common Issues

**401 Unauthorized**
- Check `pod_token` environment variable
- Verify API server is running with correct token

**503 Service Unavailable**
- For RAG endpoints: Set `OPENAI_API_KEY`
- For other endpoints: Check API server status

**Individual Agent Tests Failing**
- Verify agents are properly registered
- Check agent configuration
- Review API server logs

**Auto-Generated Variables Not Working**
- Clear environment variables and let collection regenerate
- Check pre-request scripts in collection settings

### Getting Help

1. Check API server logs for detailed error information
2. Use "Health Check" to verify API connectivity
3. Review individual agent configuration with "Get Agent Info"
4. Test with simple requests first, then complex scenarios

---

**Happy Testing! 🎉**

This collection is designed to make your development workflow faster and more efficient by enabling individual agent testing. No more waiting for full crew executions - test each agent separately and iterate quickly!
