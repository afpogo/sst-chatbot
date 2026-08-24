from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> int:
    print(f"> {' '.join(command)}")
    completed = subprocess.run(command, cwd=ROOT_DIR)
    return completed.returncode


def main() -> int:
    commands = [
        [sys.executable, "scripts/ards_check.py"],
        [sys.executable, "-m", "pytest"],
        [sys.executable, "scripts/smoke_governed_rag.py"],
        [sys.executable, "scripts/smoke_stakeholder_rag.py"],
        [sys.executable, "scripts/smoke_llm_provider_connection.py"],
    ]

    for command in commands:
        return_code = run(command)
        if return_code != 0:
            return return_code

    print("Repository check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
