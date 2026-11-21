"""Centralized Task Management System for Antigravity CDO."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    BLOCKED = "BLOCKED"
    ASSIGNED = "ASSIGNED"
    RUNNING = "RUNNING"
    WAITING_QUOTA = "WAITING_QUOTA"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    REVIEWING = "REVIEWING"
    REWORK = "REWORK"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class TaskRecord:
    task_id: str
    title: str
    description: str
    objective: str
    priority: str = "medium"
    dependencies: list[str] = field(default_factory=list)
    assigned_agent: str = ""
    assigned_terminal: str = ""
    selected_model: str = ""
    allowed_files: list[str] = field(default_factory=list)
    prohibited_files: list[str] = field(default_factory=list)
    expected_outputs: list[str] = field(default_factory=list)
    verification_commands: list[str] = field(default_factory=list)
    retry_limit: int = 2
    retries_used: int = 0
    current_status: TaskStatus = TaskStatus.PENDING
    execution_history: list[dict[str, Any]] = field(default_factory=list)
    validation_results: dict[str, Any] = field(default_factory=dict)
    approval_status: str = "PENDING"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["current_status"] = self.current_status.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskRecord:
        copy = dict(data)
        copy["current_status"] = TaskStatus(copy.get("current_status", "PENDING"))
        return cls(**copy)


class TaskManager:
    """Manages task lifecycle, retry limits, and strict QA-gated approval."""

    def __init__(self, registry_path: Path | str) -> None:
        self.registry_path = Path(registry_path)
        self.tasks: dict[str, TaskRecord] = {}
        if self.registry_path.exists():
            self._load()

    def _load(self) -> None:
        raw = json.loads(self.registry_path.read_text(encoding="utf-8"))
        for item in raw.get("tasks", []):
            rec = TaskRecord.from_dict(item)
            self.tasks[rec.task_id] = rec

    def save(self) -> None:
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"tasks": [t.to_dict() for t in self.tasks.values()]}
        self.registry_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def register(self, task: TaskRecord) -> None:
        self.tasks[task.task_id] = task

    def record_execution_finish(
        self, task_id: str, exit_code: int, summary: dict[str, Any]
    ) -> TaskRecord:
        task = self.tasks[task_id]
        task.execution_history.append({"exit_code": exit_code, **summary})
        # Exit code 0 never auto-approves; always transitions to REVIEWING.
        if exit_code == 0:
            task.current_status = TaskStatus.REVIEWING
        else:
            if task.retries_used < task.retry_limit:
                task.retries_used += 1
                task.current_status = TaskStatus.REWORK
            else:
                task.current_status = TaskStatus.FAILED
        return task

    def finalize_qa(
        self, task_id: str, *, passed: bool, validation_results: dict[str, Any]
    ) -> TaskRecord:
        task = self.tasks[task_id]
        if task.current_status != TaskStatus.REVIEWING:
            raise ValueError(
                f"Task '{task_id}' must be in REVIEWING before QA finalization (current: {task.current_status.value})."
            )
        task.validation_results = validation_results
        if passed:
            task.current_status = TaskStatus.APPROVED
            task.approval_status = "APPROVED_BY_CDO"
        else:
            if task.retries_used < task.retry_limit:
                task.retries_used += 1
                task.current_status = TaskStatus.REWORK
            else:
                task.current_status = TaskStatus.REJECTED
                task.approval_status = "REJECTED"
        return task
