from __future__ import annotations

import sys
from pathlib import Path

from repository.scanner import RepositoryScanner


def main() -> None:
    """
    Scan the repository passed on the command line.

    Example:
        python -m tests.test_phase4_repository .
    """

    if len(sys.argv) < 2:
        repository_path = Path.cwd()
    else:
        repository_path = Path(sys.argv[1])

    print("=" * 60)
    print("PHASE 4 — REPOSITORY DISCOVERY TEST")
    print("=" * 60)

    print(f"\nRepository: {repository_path.resolve()}\n")

    scanner = RepositoryScanner(repository_path)

    print("Scanning repository...")
    context = scanner.scan()

    print("✓ Repository scan complete\n")

    print(context.summary())

    print("\n" + "=" * 60)
    print("PHASE 4 TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()