---
name: vector
description: Vector configuration and deployment for log aggregation. Use when generating, testing, validating, and deploying Vector configurations for multi-line log aggregation and filtering. Focus on transforms configuration (reduce for aggregation, filter for error filtering).
---

# Vector Configuration Skill

Vector is a high-performance log aggregation tool. This skill guides you in generating, testing, and deploying Vector configurations for collecting and filtering error logs from Docker containers.

## Core Concepts

### Vector Architecture

Vector processes logs through a pipeline:
```
Source → Transforms → Sink
```

- **Source**: Where logs come from (docker_logs, file, stdin)
- **Transforms**: Process and modify logs (reduce, filter, remap)
- **Sink**: Where logs go (http, console, file)

### Multi-line Log Aggregation

The main challenge is aggregating multi-line error logs (stack traces) into single events:

**Example Input** (4 separate log lines):
```
2025-01-15 10:30:05 [ERROR] Database connection failed
Traceback (most recent call last):
  File "app.py", line 42, in connect_to_db
ConnectionRefusedError: Connection refused
```

**Expected Output** (1 aggregated event):
```json
{
  "message": "2025-01-15 10:30:05 [ERROR] Database connection failed\nTraceback (most recent call last):\n  File \"app.py\", line 42, in connect_to_db\nConnectionRefusedError: Connection refused"
}
```

## Key Configuration Sections

### 1. Source Configuration

**For Testing** (stdin source):
```yaml
sources:
  test_logs:
    type: stdin
    decoding:
      codec: bytes
```

**For Production** (docker_logs source):
```yaml
sources:
  app_logs:
    type: docker_logs
    include_containers: ["my-app-container"]
```

### 2. Transform: Reduce (Aggregation)

The `reduce` transform aggregates multi-line logs (Example):

```yaml
transforms:
  merged_logs:
    type: reduce
    inputs: ["app_logs"]  # If test, use test_logs, else app_logs
    group_by: []  # Empty for stdin, ["container_id"] for docker_logs
    merge_strategies:
      message: "concat"  # Concatenate messages
    starts_when: |
      msg = to_string(.message) ?? ""

      # Continuation lines (stack trace) should NOT trigger new event
      is_continuation = match(msg, r'^(    |\t|at |File "|Traceback \(most|Caused by:)')

      # New event starts when: NOT continuation AND has standard log prefix
      !is_continuation && match(msg, r'^(\d{4}-\d{2}-\d{2}|\[\d+\]|\d{2}:\d{2}:\d{2}|INFO|DEBUG|WARN|CRITICAL)')
    expire_after_ms: 1000  # End aggregation after 1 second of inactivity
```

**Key Points**:
- `group_by`: How to group log streams
  - For stdin: `[]` (no grouping)
  - For docker_logs: `["container_id"]` (group by container)
- `starts_when`: VRL expression that returns `true` when a new event should start
  - Should return `false` for continuation lines (indented stack trace)
  - Should return `true` for new log entries (with timestamps, log levels, etc.)
- `expire_after_ms`: Timeout to end aggregation (1000ms = 1 second)

### 3. Transform: Filter (Error Filtering)

The `filter` transform removes non-error logs (Example):

```yaml
transforms:
  error_only_filter:
    type: filter
    inputs: ["merged_logs"]
    condition: |
      msg = downcase(to_string(.message) ?? "")

      # Detect HTTP access logs: "IP:PORT - "METHOD PATH" STATUS"
      is_http_access = match(msg, r'\d+\.\d+\.\d+\.\d+:\d+ - "[A-Z]+ [^"]+?" \d{3}')

      # HTTP access logs must have real errors
      http_has_real_error = is_http_access && match(msg, r'(traceback|exception|refused|connection|denied|timeout|error \(|caused by|failed)')

      # Non-HTTP logs just need error keywords
      has_error_keyword = contains(msg, "error") ||
                           contains(msg, "exception") ||
                           contains(msg, "traceback") ||
                           contains(msg, "critical") ||
                           contains(msg, "fatal")

      # Pass through: (non-HTTP with errors) OR (HTTP with real errors)
      (!is_http_access && has_error_keyword) || http_has_real_error
```

**Key Points**:
- Filter condition should return `true` for logs to keep
- Common error keywords: `error`, `exception`, `traceback`, `critical`, `fatal`
- HTTP access logs with 5xx status should be kept if they contain error details

### 4. Sink Configuration

**For Testing** (console sink):
```yaml
sinks:
  test_output:
    type: console
    inputs: ["error_only_filter"]
    encoding:
      codec: json
```

**For Production** (HTTP sink):
```yaml
sinks:
  http_output:
    type: http
    inputs: ["error_only_filter"]
    uri: http://172.17.0.1:7000/vector/ingest
    encoding:
      codec: json
    batch:
      max_events: 10
      timeout_secs: 5
    request:
      timeout_secs: 10
      retry_attempts: 3
```

## Common Log Patterns

### Python Stack Traces
```
Traceback (most recent call last):
  File "app.py", line 42, in <module>
    some_function()
ValueError: Something went wrong
```

**Pattern**: Lines starting with `Traceback`, `  File`, or indentation (4 spaces)

### Java Stack Traces
```
Exception in thread "main" java.lang.NullPointerException
    at com.example.Class.method(Class.java:123)
    at com.example.Other.method(Other.java:456)
Caused by: java.sql.SQLException: Connection failed
```

**Pattern**: Lines starting with `Exception`, `Caused by:`, or indentation (4 spaces)

### HTTP Access Logs
```
172.18.0.1:38530 - "GET /api/stats HTTP/1.1" 500
172.18.0.1:38530 - "POST /api/tasks HTTP/1.1" 200
```

**Pattern**: `IP:PORT - "METHOD PATH PROTO" STATUS`

## Workflow: Generate and Deploy Vector Config

### Step 1: Analyze Log Samples

Examine the provided error logs to identify:
- Log format (timestamps, log levels, structure)
- Stack trace patterns (indentation, prefixes)
- Error indicators (keywords, status codes)

### Step 2: Generate Test Configuration

Create a Vector configuration with:
- **Source**: `stdin` (for testing)
- **Transforms**: `reduce` (aggregation) + `filter` (error filtering)
- **Sink**: `console` (for output inspection)

**Example**:
```yaml
sources:
  test_logs:
    type: stdin
    decoding:
      codec: bytes

transforms:
  merged_logs:
    type: reduce
    inputs: ["test_logs"]
    group_by: []
    merge_strategies:
      message: "concat"
    starts_when: |
      msg = to_string(.message) ?? ""
      is_continuation = match(msg, r'^(    |\t|at |File "|Traceback \(most|Caused by:)')
      !is_continuation && match(msg, r'^(\d{4}-\d{2}-\d{2}|\[\d+\]|\d{2}:\d{2}:\d{2}|INFO|DEBUG|WARN|CRITICAL)')
    expire_after_ms: 1000

  error_only_filter:
    type: filter
    inputs: ["merged_logs"]
    condition: |
      msg = downcase(to_string(.message) ?? "")
      contains(msg, "error") || contains(msg, "exception") || contains(msg, "traceback")

sinks:
  test_output:
    type: console
    inputs: ["error_only_filter"]
    encoding:
      codec: json
```

### Step 3: Get Vector Image

Use `get_vector_image()` to get the correct Docker image:

```python
vector_image = get_vector_image()
```

### Step 4: Test Configuration

Use the `test_vector_config` tool with the image:

```python
result = test_vector_config(
    config_yaml=test_config,
    docker_image=vector_image,
    test_logs=[
        '2025-01-15 10:30:05 [ERROR] Database connection failed',
        'Traceback (most recent call last):',
        '  File "app.py", line 42',
        'ConnectionRefusedError: Connection refused'
    ]
)
```

### Step 5: Analyze Output

Examine `result['stdout']` to verify:
1. **Aggregation**: Multiple input lines → Single output event
2. **Completeness**: Stack trace is complete (no missing lines)
3. **Filtering**: Error logs kept, normal logs filtered

**Good Output Example**:
```json
{"message":"2025-01-15 10:30:05 [ERROR] Database connection failed\nTraceback (most recent call last):\n  File \"app.py\", line 42\nConnectionRefusedError: Connection refused"}
```

**Bad Output Examples**:
- Multiple separate events → Aggregation failed
- Incomplete stack trace → `starts_when` condition incorrect
- Normal HTTP 200 logs → Filter condition incorrect

### Step 6: Iterate if Needed

If output is incorrect:
1. **Aggregation issues**: Adjust `starts_when` condition
2. **Filtering issues**: Adjust `condition` in filter
3. **Timeout issues**: Adjust `expire_after_ms`

Re-test until configuration is correct.

### Step 7: Generate Production Config

Convert the test configuration to production configuration manually:

**Important**: First, get the monitored container name:
```python
container_name = get_monitored_container()
```

**Changes needed**:
1. **Source**: `stdin` → `docker_logs`
2. **Sink**: `console` → `http`
3. **Grouping**: `[]` → `["container_id"]` (for docker_logs)

**Example conversion**:

Test config (stdin):
```yaml
sources:
  test_logs:
    type: stdin
    decoding:
      codec: bytes
```

Production config (docker_logs):
```yaml
sources:
  app_logs:
    type: docker_logs
    include_containers: ["target-container"]  # Use get_monitored_container()
```

**Transform updates**:
- Change `inputs: ["test_logs"]` to `inputs: ["app_logs"]`
- Change `group_by: []` to `group_by: ["container_id"]`

**Sink updates**:
```yaml
sinks:
  http_output:
    type: http
    inputs: ["error_only_filter"]
    uri: http://172.17.0.1:7000/vector/ingest
    encoding:
      codec: json
    batch:
      max_events: 10
      timeout_secs: 5
    request:
      timeout_secs: 10
      retry_attempts: 3
```

Use the `write_file` tool to save the production configuration.

### Step 8: Deploy Vector

**Important**: Follow the path mapping rules below when deploying.

**Path mapping rules**:
- **Save config**: Use `/local/` prefix (e.g., `/local/vector.yaml`)
- **Mount volume**: Use relative path (e.g., `./vector.yaml`)

**Deployment steps**:

1. Get Vector image:
   ```python
   vector_image = get_vector_image()
   ```

2. Save production config (use `/local/` prefix):
   ```python
   write_file("/local/vector.yaml", production_config)
   ```

3. Start container (mount with relative path):
   ```python
   result = start_container(
       docker_image=vector_image,
       container_name="auperator-vector",
       volume_mounts={"./vector.yaml": "/etc/vector/vector.yaml"}
   )
   ```

## VRL (Vector Remap Language) Tips

### Common Patterns

**Check if line is indented** (continuation line):
```vrl
match(msg, r'^    ')  # 4 spaces
match(msg, r'^\t')    # Tab
```

**Check if line has standard log prefix**:
```vrl
match(msg, r'^\d{4}-\d{2}-\d{2}')  # Date: 2025-01-15
match(msg, r'^\d{2}:\d{2}:\d{2}')  # Time: 10:30:05
match(msg, r'^\[INFO\]')            # [INFO]
```

**Case-insensitive search**:
```vrl
downcase(msg) =~ "error"
```

**Safe string conversion**:
```vrl
to_string(.message) ?? ""
```

## Troubleshooting

### Problem: Logs not aggregated

**Symptoms**: Multiple output events for one error

**Solutions**:
- Check `starts_when` condition
- Ensure continuation lines return `false`
- Ensure new log lines return `true`

### Problem: Incomplete stack traces

**Symptoms**: Stack trace cut off prematurely

**Solutions**:
- Increase `expire_after_ms` (default: 1000ms)
- Check if continuation patterns are correct

### Problem: Normal logs not filtered

**Symptoms**: HTTP 200 logs in output

**Solutions**:
- Check filter `condition`
- Ensure error keywords are correct
- Add additional filtering logic

### Problem: Error logs filtered out

**Symptoms**: No output despite errors in input

**Solutions**:
- Check if error keywords match log format
- Use case-insensitive matching (`downcase`)
- Test filter condition separately

## Best Practices

1. **Start with test configuration** using stdin/console
2. **Test with real log samples** from the target application
3. **Verify output manually** before generating production config
4. **Use appropriate grouping**:
   - Empty `[]` for stdin/file sources
   - `["container_id"]` for docker_logs
5. **Set reasonable timeout**: 1000ms is usually sufficient
6. **Test edge cases**:
   - Concurrent errors from multiple containers
   - Mixed log formats
   - Very long stack traces
7. **Monitor in production**: Check Vector logs for errors or warnings

## Available Tools

### Vector Tools
- **test_vector_config**: Test configuration with sample logs
- **get_vector_image**: Get the Docker image ID or name for Vector (use this to get the correct image for testing and deployment)

### Docker Tools (for deployment and monitoring)
- **get_monitored_container**: Get the name of the monitored container (use this when generating production config)
- **start_container**: Start a Docker container (for Vector deployment)
- **stop_container**: Stop a running Docker container

### Filesystem Tools
- **write_file**: Write the production configuration to a file

**Important**:
- Always use `get_vector_image()` to get the correct Vector Docker image before running tests or deploying. Do not hardcode image names in your commands.
- Always use `get_monitored_container()` to get the monitored container name when generating production config. Do not hardcode container names.
