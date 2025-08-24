#!/usr/bin/env python3
import os
import sys

# Ensure repo root is on sys.path when running from scripts/
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from manager.task_manager import TaskManager


def main() -> int:
    tm = TaskManager()
    path = tm.write_status()
    print(f"Wrote {path}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
