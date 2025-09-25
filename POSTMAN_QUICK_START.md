# 🚀 Cage API Postman Collection - Quick Start

## ⚡ 30-Second Setup

1. **Import Collection**
   - Import `postman_collection.json` into Postman
   - Collection: "Cage Pod API - Complete Collection"

2. **Set Environment Variables**
   ```
   base_url: http://localhost:8000
   pod_token: dev-token
   ```

3. **Start Testing Individual Agents**
   - Go to "🤖 Individual Agents (NEW!)" folder
   - Run "List Available Agents"
   - Try "Test Individual Agent - Planner"

## 🎯 Key Features

### ✨ Individual Agent Testing (The Main Feature!)
**This is exactly what you requested** - test each agent separately without running the full crew:

- **POST** `/crew/request` - Test any agent individually
- **GET** `/crew/agents` - List all available agents
- **GET** `/crew/agents/{name}` - Get specific agent info

### 🤖 Available Agents
- **planner**: Creates detailed execution plans
- **implementer**: Handles file operations and code changes  
- **reviewer**: Reviews code quality and compliance
- **committer**: Manages Git operations and commits

### 🔧 Auto-Generated Variables
- `task_id`: Auto-generated with timestamp
- `agent_name`: Set from agent list response
- Global authentication handling
- Comprehensive test scripts

## 📋 Collection Structure

### 🏥 System Health
- Health Check (no auth required)
- About (pod information)

### 🤖 Individual Agents (NEW!)
- **List Available Agents** ⭐
- **Test Individual Agent - Planner** ⭐
- **Test Individual Agent - Implementer** ⭐
- **Test Individual Agent - Reviewer** ⭐
- **Test Individual Agent - Committer** ⭐
- **Get Agent Info**

### 📋 Task Management
- Create Task (with auto-generated ID)
- List Tasks
- Get Task

### 📁 File Operations
- Create File (INSERT operation)
- Read File (GET operation)

### 🔀 Git Operations
- Git Status
- Commit Changes (conventional format)

## 🎯 Perfect for Reducing Feedback Loops

### Before (Traditional Crew)
```
1. Create full crew plan
2. Execute all agents in sequence
3. Wait for entire crew to complete
4. Debug issues across multiple agents
5. Repeat entire process for changes
```

### Now (Individual Agent Testing)
```
1. Test specific agent with "Test Individual Agent"
2. Get immediate feedback
3. Iterate on single agent configuration
4. Move to next agent when ready
5. Much faster development cycle!
```

## 📖 Example Usage

### Test Planner Agent
```json
POST /crew/request
{
    "agent": "planner",
    "request": "Create a plan for user authentication system"
}
```

### Test Implementer Agent
```json
POST /crew/request
{
    "agent": "implementer", 
    "request": "Create a Python file called 'auth.py' with login function"
}
```

### Test Reviewer Agent
```json
POST /crew/request
{
    "agent": "reviewer",
    "request": "Review the authentication code for security issues"
}
```

### Test Committer Agent
```json
POST /crew/request
{
    "agent": "committer",
    "request": "Commit the authentication changes with proper message"
}
```

## 🔧 Tips & Tricks

### 1. Chain Requests
- "List Available Agents" sets `agent_name` variable
- "Create Task" sets `task_id` variable
- Use variables in subsequent requests

### 2. Use Test Scripts
- All requests have comprehensive test scripts
- Check console for detailed logging
- Tests validate response structure and data

### 3. Environment Setup
- Variables auto-generate if not set
- Override with your specific values
- Use different environments for dev/staging/prod

### 4. Error Handling
- Test scripts handle common errors gracefully
- 503 errors expected for RAG without OPENAI_API_KEY
- Console logs provide debugging information

## 🚨 Troubleshooting

### Common Issues

**401 Unauthorized**
- Check `pod_token` environment variable
- Verify API server is running

**Individual Agent Tests Failing**
- Verify agents are registered: run "List Available Agents"
- Check API server logs for detailed errors
- Ensure modular agent system is initialized

**Auto-Variables Not Working**
- Clear environment variables to trigger regeneration
- Check pre-request scripts in collection settings

## 🎉 Success!

You now have a comprehensive Postman collection that enables **individual agent testing** - exactly what you requested for reducing feedback loops and improving development efficiency!

**No more waiting for full crew execution - test each agent separately and iterate quickly!** 🚀
