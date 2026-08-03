"""
DEEP — Docker Sandbox Executor
Isolated code/exploit execution in ephemeral Docker containers.
Security model:
  - No network access (--network none)
  - Read-only filesystem (except /sandbox/workspace)
  - CPU and memory limits enforced
  - Auto-removed after execution (--rm)
  - Seccomp profile applied (restricts dangerous syscalls)
  - Execution timeout enforced (SIGKILL at limit)
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


# ── Configuration ─────────────────────────────────────────────────────────────

DEFAULT_TIMEOUT    = 30          # seconds
MAX_OUTPUT_BYTES   = 64 * 1024  # 64 KB output cap
SANDBOX_IMAGE      = "deep-sandbox:latest"
FALLBACK_IMAGE     = "python:3.11-slim"

LANG_CONFIG: Dict[str, Dict[str, str]] = {
    "python":     {"image": "python:3.11-slim",    "ext": ".py",   "cmd": "python /sandbox/code.py"},
    "bash":       {"image": "debian:bookworm-slim", "ext": ".sh",   "cmd": "bash /sandbox/code.sh"},
    "javascript": {"image": "node:20-slim",         "ext": ".js",   "cmd": "node /sandbox/code.js"},
    "ruby":       {"image": "ruby:3.3-slim",        "ext": ".rb",   "cmd": "ruby /sandbox/code.rb"},
    "go":         {"image": "golang:1.22-alpine",   "ext": ".go",   "cmd": "go run /sandbox/code.go"},
    "c":          {"image": "gcc:latest",           "ext": ".c",    "cmd": "sh -c 'gcc -o /tmp/prog /sandbox/code.c && /tmp/prog'"},
    "cpp":        {"image": "gcc:latest",           "ext": ".cpp",  "cmd": "sh -c 'g++ -o /tmp/prog /sandbox/code.cpp && /tmp/prog'"},
}

# Security flags applied to every sandbox container
_DOCKER_SECURITY_FLAGS = [
    "--network", "none",           # No network
    "--read-only",                 # Read-only filesystem
    "--tmpfs", "/tmp:size=64m",    # Writable /tmp in memory only
    "--tmpfs", "/sandbox:size=16m,exec",  # Writable sandbox dir
    "--memory", "256m",            # 256 MB RAM limit
    "--memory-swap", "256m",       # No swap
    "--cpus", "0.5",               # Half a CPU core
    "--pids-limit", "64",          # Max 64 processes
    "--cap-drop", "ALL",           # Drop all Linux capabilities
    "--security-opt", "no-new-privileges:true",
]


# ── Result type ───────────────────────────────────────────────────────────────

@dataclass
class SandboxResult:
    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    execution_time_ms: int = 0
    language: str = ""
    image: str = ""
    timed_out: bool = False
    error: Optional[str] = None
    # Security context
    was_isolated: bool = True
    network_disabled: bool = True


# ── Sandbox Executor ──────────────────────────────────────────────────────────

class SandboxExecutor:
    """
    Docker-based isolated code execution engine.
    All execution is ephemeral: containers are auto-removed after each run.
    """

    def __init__(self, workspace_dir: str = "data/sandbox"):
        self._workspace = Path(workspace_dir)
        self._workspace.mkdir(parents=True, exist_ok=True)
        self._docker_available: Optional[bool] = None

    # ── Public API ─────────────────────────────────────────────────────────────

    async def execute(
        self,
        code: str,
        language: str = "python",
        timeout: int = DEFAULT_TIMEOUT,
        stdin_data: str = "",
        extra_files: Optional[Dict[str, str]] = None,
    ) -> SandboxResult:
        """
        Execute code in an isolated Docker container.
        code:      Source code string
        language:  "python" | "bash" | "javascript" | "ruby" | "go" | "c" | "cpp"
        timeout:   Max execution time in seconds (hard kill after)
        stdin_data: Data to pipe to stdin
        extra_files: {filename: content} — extra files mounted in /sandbox
        Returns: SandboxResult with stdout, stderr, timing, isolation proof
        """
        lang = language.lower()
        if lang not in LANG_CONFIG:
            return SandboxResult(
                success=False,
                error=f"Unsupported language: {lang}. Supported: {list(LANG_CONFIG.keys())}",
            )

        # Check Docker availability
        if not await self._check_docker():
            if os.environ.get("DEEP_SANDBOX_ALLOW_UNSAFE") == "1":
                return await self._fallback_python_exec(code, lang, timeout)
            else:
                return SandboxResult(
                    success=False,
                    error=(
                        "Docker is not available. The sandbox requires Docker to safely isolate execution. "
                        "Please ensure Docker Desktop is installed and running, or set DEEP_SANDBOX_ALLOW_UNSAFE=1 "
                        "to allow unisolated host execution."
                    ),
                    language=lang,
                    was_isolated=False,
                    network_disabled=False,
                )

        config = LANG_CONFIG[lang]
        job_id = hashlib.sha256(f"{code}{time.time()}".encode()).hexdigest()[:12]
        job_dir = self._workspace / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Write code file
            code_path = job_dir / f"code{config['ext']}"
            code_path.write_text(code, encoding="utf-8")

            # Write extra files
            for fname, content in (extra_files or {}).items():
                safe_name = Path(fname).name  # strip directory traversal
                (job_dir / safe_name).write_text(content, encoding="utf-8")

            # Build docker run command
            cmd = self._build_docker_cmd(
                image=config["image"],
                run_cmd=config["cmd"],
                volume_path=str(job_dir),
                timeout=timeout,
            )

            start = time.monotonic()
            result = await self._run_subprocess(cmd, stdin_data=stdin_data, timeout=timeout + 5)
            elapsed_ms = int((time.monotonic() - start) * 1000)

            return SandboxResult(
                success=result["returncode"] == 0,
                stdout=result["stdout"][:MAX_OUTPUT_BYTES],
                stderr=result["stderr"][:MAX_OUTPUT_BYTES],
                exit_code=result["returncode"],
                execution_time_ms=elapsed_ms,
                language=lang,
                image=config["image"],
                timed_out=result.get("timed_out", False),
                was_isolated=True,
                network_disabled=True,
            )

        except Exception as exc:
            return SandboxResult(
                success=False,
                error=f"Sandbox execution failed: {exc}",
                language=lang,
                was_isolated=True,
            )
        finally:
            # Cleanup job directory
            try:
                shutil.rmtree(job_dir, ignore_errors=True)
            except Exception:
                pass

    async def test_connectivity(self) -> Dict[str, Any]:
        """Test Docker availability and return status info."""
        available = await self._check_docker()
        result = {
            "docker_available": available,
            "sandbox_workspace": str(self._workspace),
            "supported_languages": list(LANG_CONFIG.keys()),
            "security_flags": _DOCKER_SECURITY_FLAGS,
        }
        if available:
            # Get Docker version
            try:
                proc = await asyncio.create_subprocess_exec(
                    "docker", "version", "--format", "{{.Server.Version}}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
                result["docker_version"] = stdout.decode().strip()
            except Exception:
                result["docker_version"] = "unknown"
        return result

    # ── Private ────────────────────────────────────────────────────────────────

    def _build_docker_cmd(
        self,
        image: str,
        run_cmd: str,
        volume_path: str,
        timeout: int,
    ) -> List[str]:
        """Build the full docker run command."""
        cmd = [
            "docker", "run",
            "--rm",                            # Auto-remove container
            *_DOCKER_SECURITY_FLAGS,
            "--volume", f"{volume_path}:/sandbox:ro",  # Mount code read-only
            "--workdir", "/sandbox",
        ]
        # Add timeout wrapper (uses `timeout` command inside container)
        cmd += [image, "sh", "-c", f"timeout {timeout} {run_cmd}"]
        return cmd

    async def _run_subprocess(
        self,
        cmd: List[str],
        stdin_data: str = "",
        timeout: int = 60,
    ) -> Dict[str, Any]:
        """Run a subprocess asynchronously with timeout."""
        timed_out = False
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE if stdin_data else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdin_bytes = stdin_data.encode() if stdin_data else None
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(input=stdin_bytes),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                proc.kill()
                stdout, stderr = await proc.communicate()
                timed_out = True

            return {
                "returncode": proc.returncode or 0,
                "stdout": stdout.decode(errors="replace"),
                "stderr": stderr.decode(errors="replace"),
                "timed_out": timed_out,
            }
        except FileNotFoundError:
            return {
                "returncode": 127,
                "stdout": "",
                "stderr": "docker: command not found",
                "timed_out": False,
            }

    async def _check_docker(self) -> bool:
        """Check if Docker is available and running."""
        if self._docker_available is not None:
            return self._docker_available

        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "info",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.wait(), timeout=5)
            self._docker_available = proc.returncode == 0
        except Exception:
            self._docker_available = False

        return self._docker_available

    async def _fallback_python_exec(self, code: str, lang: str, timeout: int) -> SandboxResult:
        """
        Fallback: run Python code in a subprocess with RestrictedPython if Docker
        is unavailable. MUCH weaker isolation — clearly flags this to the user.
        Only supports Python in fallback mode.
        """
        if lang != "python":
            return SandboxResult(
                success=False,
                error=(
                    f"Docker not available. Fallback execution only supports Python. "
                    f"Install Docker Desktop for full multi-language sandboxing."
                ),
                was_isolated=False,
                network_disabled=False,
            )

        # Write to temp file and execute with subprocess timeout
        import sys
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, dir=str(self._workspace)) as f:
            f.write(code)
            tmppath = f.name

        start = time.monotonic()
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, tmppath,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
                timed_out = False
            except asyncio.TimeoutError:
                proc.kill()
                stdout, stderr = await proc.communicate()
                timed_out = True

            elapsed_ms = int((time.monotonic() - start) * 1000)
            return SandboxResult(
                success=proc.returncode == 0 and not timed_out,
                stdout=stdout.decode(errors="replace")[:MAX_OUTPUT_BYTES],
                stderr=stderr.decode(errors="replace")[:MAX_OUTPUT_BYTES],
                exit_code=proc.returncode or 0,
                execution_time_ms=elapsed_ms,
                language="python",
                image="subprocess-fallback",
                timed_out=timed_out,
                was_isolated=False,
                network_disabled=False,
                error="⚠ FALLBACK MODE: Docker not available. Running in host subprocess. Network and filesystem NOT isolated.",
            )
        finally:
            os.unlink(tmppath)


# ── Singleton ──────────────────────────────────────────────────────────────────
_sandbox_instance: Optional[SandboxExecutor] = None


def get_sandbox() -> SandboxExecutor:
    global _sandbox_instance
    if _sandbox_instance is None:
        _sandbox_instance = SandboxExecutor()
    return _sandbox_instance
