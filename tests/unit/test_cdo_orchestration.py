"""Tests for CDO orchestration: OpenCodeAdapter, TaskManager, and ConcurrencyManager."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.orchestration.opencode_adapter import OpenCodeAdapter
from tools.orchestration.task_manager import TaskManager, TaskRecord, TaskStatus
from tools.orchestration.worktree_manager import ConcurrencyConflictError, ConcurrencyManager


def test_opencode_adapter_discover_and_forbidden_flag_block() -> None:
    adapter = OpenCodeAdapter()
    info = adapter.discover()
    assert info.name == "opencode"
    assert info.version

    caps = adapter.capabilities()
    assert caps.headless is True
    assert caps.json_output is True
    assert "--auto" in caps.forbidden_flags

    cmd = adapter.build_command(
        "Inspect tests", work_dir=".", model="opencode/beam-free", agent="explore"
    )
    assert cmd[1:4] == ["run", "--format", "json"]
    assert "--auto" not in cmd

    with pytest.raises(ValueError, match="Forbidden flag"):
        adapter.build_command("Bad", work_dir=".", files=["--auto"])


def test_task_manager_exit_zero_requires_qa_and_respects_retry_limit(tmp_path: Path) -> None:
    mgr = TaskManager(tmp_path / "tasks.json")
    mgr.register(
        TaskRecord(
            task_id="T-1",
            title="Test task",
            description="Desc",
            objective="Obj",
            retry_limit=2,
        )
    )

    # Exit code 0 moves to REVIEWING, never directly APPROVED
    rec = mgr.record_execution_finish("T-1", exit_code=0, summary={"elapsed_ms": 100})
    assert rec.current_status == TaskStatus.REVIEWING

    # QA failure triggers REWORK (retry 1)
    rec = mgr.finalize_qa("T-1", passed=False, validation_results={"pytest": "failed"})
    assert rec.current_status == TaskStatus.REWORK
    assert rec.retries_used == 1

    # Second run succeeds QA -> APPROVED
    mgr.record_execution_finish("T-1", exit_code=0, summary={"elapsed_ms": 90})
    rec = mgr.finalize_qa("T-1", passed=True, validation_results={"pytest": "passed"})
    assert rec.current_status == TaskStatus.APPROVED
    mgr.save()
    assert (tmp_path / "tasks.json").exists()


def test_concurrency_manager_enforces_limit_and_disjoint_files() -> None:
    cm = ConcurrencyManager(max_concurrent=2)
    cm.acquire("T-1", ["src/mvte/a.py"])
    with pytest.raises(ConcurrencyConflictError, match="overlaps"):
        cm.acquire("T-2", ["src/mvte/a.py"])

    cm.acquire("T-2", ["src/mvte/b.py"])
    with pytest.raises(ConcurrencyConflictError, match="Concurrency limit"):
        cm.acquire("T-3", ["src/mvte/c.py"])

    cm.release("T-1")
    cm.acquire("T-3", ["src/mvte/c.py"])
