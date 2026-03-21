INITIALIZE_PROMPT = """Please explore the target codebase and create a AUPERATOR.md file to help future error diagnosis and remediation.

## Your Task

1. Use the Daytona sandbox to explore the target repository
2. Analyze the project to understand:
   - Build, test, and run commands
   - Application architecture and request flow
   - Error handling and logging patterns
   - Development workflow and conventions

3. Save the AUPERATOR.md file to the **local filesystem** (not in the sandbox)

## File Location

Save to: `./AUPERATOR.md`

This file will be loaded as project memory (static memory) for future error analysis tasks.

## What to Include

Focus on practical information that helps quickly locate and fix errors:
- Essential commands (build, test, run)
- Key components and how they interact
- Common error patterns and where they originate
- Configuration and deployment specifics

Skip generic practices and extensive file listings."""
