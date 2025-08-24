#!/usr/bin/env python3
import os
import sys

# Ensure repo root is on sys.path when running from scripts/
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from manager.task_manager import TaskManager


def main() -> int:
    tm = TaskManager()
    results = tm.validate_tasks()
    failed = False
    for r in results:
        name = r.path.split('/')[-1]
        if r.valid:
            print(f"OK: {name}")
        else:
            failed = True
            print(f"INVALID: {name}")
            for e in r.errors:
                print(f"  - {e}")
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
