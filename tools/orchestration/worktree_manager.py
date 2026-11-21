"""Concurrency and Git Worktree isolation guard for Antigravity CDO."""

from __future__ import annotations

from pathlib import PurePosixPath


class ConcurrencyConflictError(ValueError):
    """Raised when parallel tasks violate concurrency limits or file isolation."""


class ConcurrencyManager:
    """Enforces max simultaneous executions and disjoint allowed_files scopes."""

    def __init__(self, max_concurrent: int = 2) -> None:
        self.max_concurrent = max_concurrent
        self._active_scopes: dict[str, set[str]] = {}

    def can_schedule(self, task_id: str, allowed_files: list[str]) -> None:
        if len(self._active_scopes) >= self.max_concurrent:
            raise ConcurrencyConflictError(
                f"Concurrency limit reached ({self.max_concurrent} active tasks)."
            )
        normalized = {str(PurePosixPath(p)) for p in allowed_files}
        for active_id, active_files in self._active_scopes.items():
            overlap = normalized & active_files
            if overlap:
                raise ConcurrencyConflictError(
                    f"Task '{task_id}' overlaps allowed_files with active task '{active_id}': {sorted(overlap)}"
                )

    def acquire(self, task_id: str, allowed_files: list[str]) -> None:
        self.can_schedule(task_id, allowed_files)
        self._active_scopes[task_id] = {str(PurePosixPath(p)) for p in allowed_files}

    def release(self, task_id: str) -> None:
        self._active_scopes.pop(task_id, None)
