from __future__ import annotations

import json
import os
from dataclasses import dataclass
from glob import glob
from typing import Any, Dict, List, Optional

from jsonschema import Draft202012Validator


@dataclass
class TaskValidationResult:
    path: str
    valid: bool
    errors: List[str]


class TaskManager:
    """Utilities for loading, validating and summarising JSON tasks."""

    def __init__(self, repo_root: Optional[str] = None) -> None:
        self.repo_root = repo_root or os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        self.tasks_dir = os.path.join(self.repo_root, "tasks")
        self.schema_path = os.path.join(self.tasks_dir, "_schema.json")
        self.status_path = os.path.join(self.tasks_dir, "_status.json")

    # -------- File IO --------
    def load_schema(self) -> Dict[str, Any]:
        with open(self.schema_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def list_task_paths(self) -> List[str]:
        all_json = glob(os.path.join(self.tasks_dir, "*.json"))
        def include(p: str) -> bool:
            base = os.path.basename(p)
            return base not in {"_schema.json", "_blank_task.json", "_status.json"}
        return sorted([p for p in all_json if include(p)])

    def load_tasks(self) -> List[Dict[str, Any]]:
        tasks: List[Dict[str, Any]] = []
        for path in self.list_task_paths():
            with open(path, "r", encoding="utf-8") as f:
                tasks.append(json.load(f))
        return tasks

    # -------- Validation --------
    def validate_tasks(self) -> List[TaskValidationResult]:
        schema = self.load_schema()
        validator = Draft202012Validator(schema)
        results: List[TaskValidationResult] = []
        for path in self.list_task_paths():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            errors = [self._format_error(e) for e in validator.iter_errors(data)]
            results.append(TaskValidationResult(path=path, valid=len(errors) == 0, errors=errors))
        return results

    @staticmethod
    def _format_error(e: Any) -> str:
        loc = "/".join(str(x) for x in e.path) or "<root>"
        return f"{loc}: {e.message}"

    # -------- Status generation --------
    def generate_status(self) -> Dict[str, Any]:
        tasks = self.load_tasks()
        active = [t for t in tasks if t.get("status") not in ("done", "abandoned")]
        active.sort(key=lambda t: t.get("updated_at", ""), reverse=True)

        def latest_work(task: Dict[str, Any]) -> str:
            changelog = task.get("changelog", [])
            if not changelog:
                return ""
            last = changelog[-1]
            return f"{last.get('timestamp', '')} — {last.get('text', '')}"

        def remaining_todo(task: Dict[str, Any]) -> List[str]:
            return [i["text"] for i in task.get("todo", []) if not i.get("checked")]

        active_entries = [
            {
                "title": t.get("title", ""),
                "status": t.get("status", ""),
                "progress_percent": int(t.get("progress_percent", 0)),
                "updated_at": t.get("updated_at", ""),
                "latest_work": latest_work(t),
                "remaining_todo": remaining_todo(t),
            }
            for t in active
        ]

        completed = [t for t in tasks if t.get("status") == "done"]
        completed.sort(key=lambda t: t.get("updated_at", ""), reverse=True)
        completed = completed[:3]
        completed_entries = [
            {
                "title": t.get("title", ""),
                "done_on": t.get("updated_at", ""),
                "summary": latest_work(t),
            }
            for t in completed
        ]

        return {"active_tasks": active_entries, "recently_completed": completed_entries}

    def write_status(self, path: Optional[str] = None) -> str:
        status = self.generate_status()
        out_path = path or self.status_path
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(status, f, indent=2, ensure_ascii=False)
        return out_path
