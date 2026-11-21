"""Initial OpenCode CLI TerminalAdapter for Antigravity CDO (Bootstrap v1)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


FORBIDDEN_FLAGS = {"--auto", "--dangerously-skip-permissions"}


@dataclass
class TerminalInfo:
    name: str
    executable: str
    version: str
    os_name: str


@dataclass
class TerminalCapabilities:
    headless: bool
    json_output: bool
    session_continuity: bool
    supported_flags: list[str]
    forbidden_flags: list[str]


@dataclass
class ExecutionHandle:
    task_id: str
    command: list[str]
    started_at: str
    process: subprocess.Popen[str] | None = field(default=None, repr=False)
    session_id: str | None = None


@dataclass
class RawExecutionResult:
    task_id: str
    exit_code: int
    stdout: str
    stderr: str
    events: list[dict[str, Any]]
    finished_at: str


class OpenCodeAdapter:
    """Safe, non-interactive adapter for OpenCode CLI v1.19+."""

    def __init__(self, executable: str | None = None) -> None:
        self._explicit_executable = executable

    def discover(self) -> TerminalInfo:
        exe = self._resolve_executable()
        proc = subprocess.run(
            [exe, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"OpenCode executable failed version check: {proc.stderr.strip()}")
        version = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else "unknown"
        return TerminalInfo(
            name="opencode",
            executable=exe,
            version=version,
            os_name=os.name,
        )

    def capabilities(self) -> TerminalCapabilities:
        return TerminalCapabilities(
            headless=True,
            json_output=True,
            session_continuity=True,
            supported_flags=[
                "--format",
                "--model",
                "--agent",
                "--file",
                "--session",
                "--continue",
                "--fork",
                "--dir",
                "--title",
            ],
            forbidden_flags=sorted(FORBIDDEN_FLAGS),
        )

    def validate_configuration(self) -> dict[str, Any]:
        info = self.discover()
        auth_proc = subprocess.run(
            [info.executable, "auth", "list"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        # Never expose raw auth details or tokens; report only boolean readiness.
        has_credentials = "credentials" in (auth_proc.stdout + auth_proc.stderr).lower()
        return {
            "valid": auth_proc.returncode == 0 and has_credentials,
            "executable": info.executable,
            "version": info.version,
            "has_credentials": has_credentials,
        }

    def build_command(
        self,
        prompt: str,
        *,
        work_dir: Path | str,
        model: str | None = None,
        agent: str | None = None,
        files: list[str] | None = None,
        session_id: str | None = None,
        continue_last: bool = False,
    ) -> list[str]:
        info = self.discover()
        cmd: list[str] = [info.executable, "run", "--format", "json", "--dir", str(work_dir)]
        if model:
            cmd.extend(["--model", model])
        if agent:
            cmd.extend(["--agent", agent])
        if session_id:
            cmd.extend(["--session", session_id])
        elif continue_last:
            cmd.append("--continue")
        for fpath in files or []:
            cmd.extend(["--file", fpath])
        cmd.append(prompt)

        for token in cmd:
            if token in FORBIDDEN_FLAGS:
                raise ValueError(f"Forbidden flag detected in command: {token}")
        return cmd

    def execute_task(
        self,
        task_id: str,
        prompt: str,
        *,
        work_dir: Path | str,
        model: str | None = None,
        agent: str | None = None,
        files: list[str] | None = None,
    ) -> ExecutionHandle:
        cmd = self.build_command(
            prompt, work_dir=work_dir, model=model, agent=agent, files=files
        )
        proc = subprocess.Popen(
            cmd,
            cwd=str(work_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return ExecutionHandle(
            task_id=task_id,
            command=cmd,
            started_at=datetime.now(timezone.utc).isoformat(),
            process=proc,
        )

    def get_status(self, handle: ExecutionHandle) -> str:
        if handle.process is None:
            return "UNKNOWN"
        code = handle.process.poll()
        if code is None:
            return "RUNNING"
        return "COMPLETED" if code == 0 else "FAILED"

    def collect_output(self, handle: ExecutionHandle, timeout: int = 300) -> RawExecutionResult:
        if handle.process is None:
            raise RuntimeError("ExecutionHandle has no active process.")
        stdout, stderr = handle.process.communicate(timeout=timeout)
        events: list[dict[str, Any]] = []
        for line in stdout.splitlines():
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return RawExecutionResult(
            task_id=handle.task_id,
            exit_code=int(handle.process.returncode or 0),
            stdout=stdout,
            stderr=stderr,
            events=events,
            finished_at=datetime.now(timezone.utc).isoformat(),
        )

    def terminate(self, handle: ExecutionHandle) -> None:
        if handle.process is not None and handle.process.poll() is None:
            handle.process.terminate()

    def continue_session(
        self,
        task_id: str,
        session_id: str,
        prompt: str,
        *,
        work_dir: Path | str,
        model: str | None = None,
    ) -> ExecutionHandle:
        cmd = self.build_command(
            prompt, work_dir=work_dir, model=model, session_id=session_id
        )
        proc = subprocess.Popen(
            cmd,
            cwd=str(work_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return ExecutionHandle(
            task_id=task_id,
            command=cmd,
            started_at=datetime.now(timezone.utc).isoformat(),
            process=proc,
            session_id=session_id,
        )

    def _resolve_executable(self) -> str:
        if self._explicit_executable and Path(self._explicit_executable).exists():
            return self._explicit_executable
        # On Windows, prefer npm\opencode.cmd over broken .bun\bin\opencode.exe shim
        npm_cmd = Path.home() / "AppData" / "Roaming" / "npm" / "opencode.cmd"
        if os.name == "nt" and npm_cmd.exists():
            return str(npm_cmd)
        found = shutil.which("opencode")
        if not found:
            raise FileNotFoundError("OpenCode CLI executable not found.")
        return found
