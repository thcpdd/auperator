INITIALIZE_PROMPT = """Please explore the target codebase and create a AUPERATOR.md file to help future error diagnosis and remediation.

## ⚠️ IMPORTANT: Dual Filesystem Access

You have access to **two separate filesystems**:

### 1. 🏖️ Sandbox Filesystem (Default)
- **Access**: All paths WITHOUT the `/local` prefix
- **Purpose**: Safe code execution and exploration
- **Example**: `/app/src/main.py` → Sandbox filesystem
- **Use for**: Reading/writing code, running commands, testing changes

### 2. 💻 Local Filesystem
- **Access**: All paths STARTING with `/local`
- **Purpose**: Persistent storage and final outputs
- **Example**: `/local/AUPERATOR.md` → Local filesystem
- **Use for**: Saving final AUPERATOR.md file that will persist

**Key Rule**:
- Explore and analyze in the **sandbox** (default paths)
- Save the final AUPERATOR.md to the **local** filesystem (use `/local` prefix)

## Your Task

1. **Explore in Sandbox**: Use the Daytona sandbox to explore the target repository
   - Use paths like `/app/src/`, `/app/package.json`, etc.
   - Run commands to understand the build/test/run process
   - Read configuration files and documentation

2. **Analyze the Project**: Understand:
   - Build, test, and run commands
   - Application architecture and request flow
   - Error handling and logging patterns
   - Development workflow and conventions
   - Key components and their interactions

3. **Save to Local Filesystem**: Write the AUPERATOR.md file to local storage
   - Use path: `/local/AUPERATOR.md` (NOT `./AUPERATOR.md`)
   - This file will persist outside the sandbox
   - It will be loaded as project memory for future error analysis

## File Location

**Save to**: `/local/AUPERATOR.md` (use the `/local` prefix!)

This file will be loaded as project memory (static memory) for future error analysis tasks.

## What to Include

Focus on practical information that helps quickly locate and fix errors:
- **Essential commands**: build, test, run, debug
- **Architecture overview**: key components and data flow
- **Error patterns**: common errors and where they originate
- **Configuration details**: environment setup and deployment
- **Code structure**: important directories and file locations

Skip generic practices and extensive file listings. Focus on actionable information specific to this project."""
