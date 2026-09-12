#!/usr/bin/env python3
"""Queue daemon CLI (implementation: src/jobqueue/daemon.py).

    .venv/bin/python scripts/queue/daemon.py start | stop | status | tick
"""
import os
import sys

sys.path[0] = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.jobqueue.daemon import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
