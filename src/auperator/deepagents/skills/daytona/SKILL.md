---
name: daytona
description: Use when code execution, file operations, or command execution in an isolated sandbox environment is needed, especially for running potentially unsafe code, testing changes, or performing Git operations
---

# Daytona Sandbox Operations

## Overview

Daytona provides isolated sandbox environments for safe code execution, file operations, and command execution. Use the `daytona_cli.py` script to interact with sandboxes - no code writing required.

## When to Use

- Executing untrusted or potentially unsafe code
- Running commands that might modify the system
- Performing file operations in an isolated environment
- Cloning and manipulating Git repositories
- Testing code changes before deployment
- Any scenario requiring isolation from the host system

## Quick Reference

| Operation | Command | Description |
|-----------|---------|-------------|
| **Create** | `execute python3 src/auperator/deepagents/skills/daytona/scripts/daytona_cli.py create` | Create new sandbox, returns `sandbox_id` |
| **Destroy** | `execute python3 .../daytona_cli.py destroy <sandbox_id>` | Terminate sandbox |
| **Info** | `execute python3 .../daytona_cli.py info <sandbox_id>` | Get sandbox status and resources |
| **List** | `execute python3 .../daytona_cli.py list` | List all active sandboxes |
| **Execute** | `execute python3 .../daytona_cli.py execute <sandbox_id> <command> [cwd] [timeout]` | Run shell command in sandbox |
| **Read** | `execute python3 .../daytona_cli.py read <sandbox_id> <path>` | Read file content |
| **Write** | `execute python3 .../daytona_cli.py write <sandbox_id> <path> <content>` | Write content to file |
| **Write Base64** | `execute python3 .../daytona_cli.py write-base64 <sandbox_id> <path> <content_b64>` | Write base64-encoded content |
| **List Files** | `execute python3 .../daytona_cli.py ls <sandbox_id> <path>` | List directory contents |
| **Delete** | `execute python3 .../daytona_cli.py delete <sandbox_id> <path>` | Delete a file |
| **Clone** | `execute python3 .../daytona_cli.py clone <sandbox_id> <repo_url> [branch] [target_dir] [username] [password]` | Clone Git repository |

**CLI Script Path**: `src/auperator/deepagents/skills/daytona/scripts/daytona_cli.py`

## Usage Workflow

### 1. Create a Sandbox
```bash
execute python3 src/auperator/deepagents/skills/daytona/scripts/daytona_cli.py create
```
Returns:
```json
{"sandbox_id": "sb-1234567890"}
```

### 2. Execute Commands
```bash
execute python3 src/auperator/deepagents/skills/daytona/scripts/daytona_cli.py execute sb-1234567890 "ls -la /workspace"
```
Returns:
```json
{
  "stdout": "...",
  "stderr": "",
  "exit_code": 0,
  "execution_time_ms": 0
}
```

### 3. Write and Read Files
```bash
# Write file
execute python3 src/auperator/deepagents/skills/daytona/scripts/daytona_cli.py write sb-1234567890 /workspace/test.py "print('hello')"

# Read file
execute python3 src/auperator/deepagents/skills/daytona/scripts/daytona_cli.py read sb-1234567890 /workspace/test.py
```
Returns:
```json
{
  "content": "print('hello')",
  "content_b64": "cHJpbnQoJ2hlbGxvJyk=",
  "path": "/workspace/test.py"
}
```

### 4. Clone Repository
```bash
execute python3 src/auperator/deepagents/skills/daytona/scripts/daytona_cli.py clone sb-1234567890 https://github.com/user/repo.git main workspace/repo
```

### 5. Always Cleanup
```bash
execute python3 src/auperator/deepagents/skills/daytona/scripts/daytona_cli.py destroy sb-1234567890
```
Returns:
```json
{"status": "destroyed", "sandbox_id": "sb-1234567890"}
```

## Common Mistakes

| Mistake | Issue | Fix |
|---------|-------|-----|
| Forgetting to destroy sandbox | Resource leak | Always call `destroy` after use |
| Not using correct path | Command not found | Use path from skill root: `src/auperator/deepagents/skills/daytona/scripts/daytona_cli.py` |
| Not handling JSON errors | Crashes on failure | Check `error_type` in response |
| Using `write` with special chars | Shell escaping issues | Use `write-base64` for complex content |

## Error Handling

All commands return JSON with `error` and `error_type` on failure:

```json
{"error": "Sandbox sb-123 not found", "error_type": "SandboxNotFoundError"}
```

**Error Types**:
- `SandboxNotFoundError`: Sandbox doesn't exist
- `SandboxCommandError`: Command execution failed
- Other: Check `error_type` for specific exception

## Example: Complete Workflow

```bash
# 1. Create sandbox
execute python3 src/auperator/deepagents/skills/daytona/scripts/daytona_cli.py create
# -> {"sandbox_id": "sb-abc123"}

# 2. Clone repo
execute python3 src/auperator/deepagents/skills/daytona/scripts/daytona_cli.py clone sb-abc123 https://github.com/user/repo.git

# 3. Run tests
execute python3 src/auperator/deepagents/skills/daytona/scripts/daytona_cli.py execute sb-abc123 "cd workspace/repo && python -m pytest"

# 4. Read results
execute python3 src/auperator/deepagents/skills/daytona/scripts/daytona_cli.py read sb-abc123 workspace/repo/test-results.txt

# 5. Cleanup
execute python3 src/auperator/deepagents/skills/daytona/scripts/daytona_cli.py destroy sb-abc123
```
