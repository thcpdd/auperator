---
name: daytona
description: Use when code execution, file operations, or command execution in an isolated sandbox environment is needed, especially for running potentially unsafe code, testing changes, or performing Git operations
---

# Daytona Sandbox Operations

## Overview

Daytona provides isolated sandbox environments for safe code execution and command execution. **Most file operations can be done through shell commands** - use the `execute` command for maximum flexibility.

## Workspace Directory

In the sandbox, the `/home/daytona` is your workspace directory. Your all operations will execute in there.

## When to Use

- Executing untrusted or potentially unsafe code
- Running commands that might modify the system
- Cloning and manipulating Git repositories
- Testing code changes before deployment
- Any scenario requiring isolation from the host system

## Usage Guidelines

**IMPORTANT**: Follow these guidelines to manage sandbox resources efficiently:

| Guideline | Description |
|-----------|-------------|
| **Reuse existing sandboxes** | Before creating a new sandbox, use `list` to check if an existing sandbox is available. Reusing sandboxes reduces resource consumption and startup time. |
| **Avoid creating unnecessary sandboxes** | Only create a new sandbox when absolutely necessary (e.g., no existing sandbox meets your needs). |
| **Avoid destroying sandboxes** | Do not use the `destroy` operation unless explicitly required. Sandboxes are designed to persist and can be reused across sessions. |

## Quick Reference

| Operation | Command | Description |
|-----------|---------|-------------|
| **Create** | `execute python3 src/auperator/deepagents/skills/daytona/scripts/daytona_proxy_cli.py create` | Create new sandbox, returns `sandbox_id` |
| **Execute** | `execute python3 .../daytona_proxy_cli.py execute <sandbox_id> <command> [cwd] [timeout]` | Run shell command in sandbox |
| **List** | `execute python3 .../daytona_proxy_cli.py list` | List all sandboxes |
| **Info** | `execute python3 .../daytona_proxy_cli.py info <sandbox_id>` | Get sandbox information |
| **Destroy** | `execute python3 .../daytona_proxy_cli.py destroy <sandbox_id>` | Terminate sandbox |

**CLI Script Path(Don't use absolute path)**: `src/auperator/deepagents/skills/daytona/scripts/daytona_proxy_cli.py`

## Usage

### 1. Create a Sandbox
```bash
execute python3 src/auperator/deepagents/skills/daytona/scripts/daytona_proxy_cli.py create
```
Returns:
```json
{"sandbox_id": "sb-1234567890"}
```

### 2. List All Sandboxes
```bash
execute python3 src/auperator/deepagents/skills/daytona/scripts/daytona_proxy_cli.py list
```
Returns:
```json
{
  "sandboxes": [
    {"sandbox_id": "sb-1234567890", "status": "running", "created_at": "..."},
    {"sandbox_id": "sb-0987654321", "status": "running", "created_at": "..."}
  ],
  "count": 2
}
```

### 3. Get Sandbox Info
```bash
execute python3 src/auperator/deepagents/skills/daytona/scripts/daytona_proxy_cli.py info sb-1234567890
```
Returns:
```json
{
  "sandbox_id": "sb-1234567890",
  "status": "running",
  "created_at": "...",
  "workspace_path": "/workspace/sb-1234567890"
}
```

### 4. Execute Commands (File Operations via Shell)
```bash
# Check file size first
execute python3 .../daytona_proxy_cli.py execute sb-1234567890 "wc -l /workspace/test.py"

# Read first 100 lines (efficient)
execute python3 .../daytona_proxy_cli.py execute sb-1234567890 "head -n 100 /workspace/test.py"

# Read last 50 lines (efficient)
execute python3 .../daytona_proxy_cli.py execute sb-1234567890 "tail -n 50 /workspace/test.py"

# Read specific lines 100-200 (efficient)
execute python3 .../daytona_proxy_cli.py execute sb-1234567890 "sed -n '100,200p' /workspace/test.py"

# List directory contents
execute python3 .../daytona_proxy_cli.py execute sb-1234567890 "ls -la /workspace"

# Write a file (using heredoc for multi-line content)
execute python3 .../daytona_proxy_cli.py execute sb-1234567890 "cat > /workspace/test.py << 'EOF'\nprint('hello')\nEOF"

# Delete a file
execute python3 .../daytona_proxy_cli.py execute sb-1234567890 "rm /workspace/test.py"

# Clone Git repository
execute python3 .../daytona_proxy_cli.py execute sb-1234567890 "git clone https://github.com/user/repo.git workspace/repo"
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

## Common File Operations (via Execute)

### Best Practices: Limit Output Size

**IMPORTANT**: Always limit the amount of data transferred to avoid performance issues.

| Goal | Command | Why |
|------|---------|-----|
| Read first N lines | `head -n 100 <path>` | Only reads beginning of file |
| Read last N lines | `tail -n 100 <path>` | Only reads end of file |
| Read specific lines | `sed -n '100,200p' <path>` | Reads specific line range |
| Count lines first | `wc -l <path>` | Check file size before reading |
| Read file around line | `sed -n '50,60p' <path>` | Read specific context (e.g., error line ±5) |

**When to use `cat`:** Only for very small files (< 1KB) that you need to read entirely.

### File Operations Reference

| Operation | Shell Command |
|-----------|--------------|
| Read first 100 lines | `head -n 100 <path>` |
| Read last 100 lines | `tail -n 100 <path>` |
| Read lines 100-200 | `sed -n '100,200p' <path>` |
| Count lines | `wc -l <path>` |
| List directory | `ls -la <path>` |
| Write single line | `echo 'content' > <path>` |
| Write multi-line | `cat > <path> << 'EOF'\ncontent\nEOF` |
| Delete file | `rm <path>` |
| Create directory | `mkdir -p <path>` |
| Move/Rename | `mv <src> <dst>` |
| Copy | `cp <src> <dst>` |
| Clone repo | `git clone <url> <path>` |
| Check git status | `git -C <path> status` |

### Example: Reading File Efficiently

```bash
# First, check file size
execute python3 .../daytona_proxy_cli.py execute sb-123 "wc -l /workspace/app.py"
# -> stdout: "1500 app.py"

# File has 1500 lines, read only relevant section
execute python3 .../daytona_proxy_cli.py execute sb-123 "sed -n '1,100p' /workspace/app.py"  # First 100 lines
execute python3 .../daytona_proxy_cli.py execute sb-123 "sed -n '1400,1500p' /workspace/app.py"  # Last 100 lines

# If error on line 750, read context around it
execute python3 .../daytona_proxy_cli.py execute sb-123 "sed -n '745,755p' /workspace/app.py"
```

## Common Mistakes

| Mistake | Issue | Fix |
|---------|-------|-----|
| Creating sandboxes without checking existing ones | Resource waste | Always run `list` first to check for available sandboxes |
| Not using correct path | Command not found | Use path from skill root: `src/auperator/deepagents/skills/daytona/scripts/daytona_proxy_cli.py` |
| Shell escaping issues | Command fails | Use single quotes for heredoc EOF: `<< 'EOF'` |
| Reading entire file with `cat` | Slow, excessive data transfer | Use `head -n N`, `tail -n N`, or `sed -n 'M,Np'` |
| Not checking file size first | May read huge files | Use `wc -l <path>` to check line count first |
| Destroying sandboxes unnecessarily | Loss of reusable resources | Avoid using `destroy` unless explicitly required |

## Error Handling

All commands return JSON with `error` and `error_type` on failure:

```json
{"error": "Sandbox sb-123 not found", "error_type": "SandboxNotFoundError"}
```

**Error Types**:
- `SandboxNotFoundError`: Sandbox doesn't exist
- `SandboxCommandError`: Command execution failed
