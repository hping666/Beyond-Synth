#!/usr/bin/env python3
"""Submit jobs from a YAML file (implementation: src/jobqueue/submit.py).

    .venv/bin/python scripts/queue/submit.py jobs.yaml [--dry-run]
"""
import os
import sys

sys.path[0] = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.jobqueue.submit import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
