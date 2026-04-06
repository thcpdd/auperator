"""Vector configuration tools for Auperator Agent.

These tools allow the agent to test and validate Vector configurations
for log aggregation and filtering.
"""

import logging
import tempfile
import os
import subprocess

from langchain.tools import tool, BaseTool

from auperator.config import settings


logger = logging.getLogger(__name__)


@tool
def test_vector_config(
    config_yaml: str,
    test_logs: list[str],
    docker_image: str = "",
    timeout: int = 20
) -> dict:
    """Test a Vector configuration by running it in a Docker container with test logs.

    This tool launches a temporary Vector container, feeds test logs via stdin,
    and returns the raw output for analysis. The Agent should examine the output
    to determine if the configuration correctly aggregates and filters logs.

    Args:
        config_yaml: Vector YAML configuration (should use stdin source and console sink)
        test_logs: List of log lines to test (each line is one log entry)
        docker_image: Docker image ID or name for Vector
        timeout: Timeout in seconds for the test (default: 10)

    Returns:
        Dictionary containing:
            - success: bool - Whether Vector ran successfully
            - exit_code: int - Container exit code
            - stdout: str - Raw stdout output (contains JSON log events)
            - stderr: str - Raw stderr output (contains Vector logs)
            - error: str | None - Error message if failed

    Example:
        >>> config = '''
        ... sources:
        ...   test_logs:
        ...     type: stdin
        ...     decoding:
        ...       codec: bytes
        ... transforms:
        ...   merged_logs:
        ...     type: reduce
        ...     inputs: ["test_logs"]
        ...     group_by: []
        ...     merge_strategies:
        ...       message: "concat"
        ...     starts_when: |
        ...       msg = to_string(.message) ?? ""
        ...       !match(msg, r'^(    |\t|at |File "|Traceback \\(most')
        ...     expire_after_ms: 1000
        ... sinks:
        ...   test_output:
        ...     type: console
        ...     inputs: ["merged_logs"]
        ...     encoding:
        ...       codec: json
        ... '''
        >>> logs = [
        ...     '2025-01-15 10:30:05 [ERROR] Database connection failed',
        ...     'Traceback (most recent call last):',
        ...     '  File "app.py", line 42',
        ...     'ConnectionRefusedError: Connection refused'
        ... ]
        >>> result = test_vector_config(config, logs)
        >>> # Agent should examine result['stdout'] to verify aggregation
    """
    # 1. 将配置写入临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_yaml)
        config_path = f.name

    try:
        # 2. 准备输入数据（每行一个日志）
        input_data = '\n'.join(test_logs)

        # 3. 构建 Docker 命令
        cmd = [
            'docker', 'run', '--rm',
            '-i',  # 交互式 stdin
            f'-v={config_path}:/etc/vector/vector.yaml:ro',
            '--name', 'vector-test',
            docker_image
        ]

        logger.info(f"Running Vector test with {len(test_logs)} log lines")

        # 4. 启动容器并发送数据
        try:
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # 发送输入并等待完成
            stdout, stderr = process.communicate(
                input=input_data,
                timeout=timeout
            )

        except subprocess.TimeoutExpired:
            process.kill()
            return {
                'success': False,
                'exit_code': -1,
                'stdout': '',
                'stderr': '',
                'error': f'Timeout after {timeout} seconds'
            }

        except Exception as e:
            return {
                'success': False,
                'exit_code': -1,
                'stdout': '',
                'stderr': '',
                'error': str(e)
            }

        # 5. 返回结果（包含原始 stdout 供 Agent 分析）
        return {
            'success': process.returncode == 0,
            'exit_code': process.returncode,
            'stdout': stdout,
            'stderr': stderr,
            'error': None if process.returncode == 0 else f'Exit code: {process.returncode}'
        }

    finally:
        # 清理临时文件
        try:
            os.unlink(config_path)
        except:
            pass


def get_tools() -> list[BaseTool]:
    return [test_vector_config]
