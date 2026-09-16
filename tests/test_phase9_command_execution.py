from __future__ import annotations
from pathlib import Path
import tempfile

from tools.terminal import run_command


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    print("=" * 60)
    print("PHASE 9 — COMMAND EXECUTION TEST")
    print("=" * 60)

    with tempfile.TemporaryDirectory(prefix="phase9_repo_") as temp_dir:
        repository_root = Path(temp_dir)

        test_script = repository_root / "test_script.py"
        test_script.write_text(
            "print('hello from repository')\n",
            encoding="utf-8",
        )

        print("\n1. Running a Python command...")
        result = run_command(
            repository_root,
            "python test_script.py",
        )

        check(
            result.success,
            result.error or "Python command failed.",
        )

        check(
            "hello from repository" in result.output,
            "Expected stdout was not captured.",
        )

        print("✓ Python command execution works")
        print("✓ STDOUT capture works")

        print("\n2. Checking repository working directory...")
        cwd_script = repository_root / "cwd_test.py"
        cwd_script.write_text(
            "from pathlib import Path\n"
            "print(Path.cwd())\n",
            encoding="utf-8",
        )

        result = run_command(
            repository_root,
            "python cwd_test.py",
        )

        check(
            result.success,
            result.error or "Working-directory test failed.",
        )

        check(
            str(repository_root).lower() in result.output.lower(),
            "Command did not execute from repository root.",
        )

        print("✓ Command executes from repository root")

        print("\n3. Capturing stderr and non-zero exit code...")
        error_script = repository_root / "error_test.py"
        error_script.write_text(
            "import sys\n"
            "print('stdout message')\n"
            "print('stderr message', file=sys.stderr)\n"
            "sys.exit(3)\n",
            encoding="utf-8",
        )

        result = run_command(
            repository_root,
            "python error_test.py",
        )

        check(
            not result.success,
            "Command with non-zero exit code should fail.",
        )

        check(
            "Exit code: 3" in result.output,
            "Exit code was not captured.",
        )

        check(
            "stdout message" in result.output,
            "STDOUT was not captured for failed command.",
        )

        check(
            "stderr message" in result.output,
            "STDERR was not captured.",
        )

        check(
            result.metadata.get("exit_code") == 3,
            "Metadata contains incorrect exit code.",
        )

        print("✓ Non-zero exit code handling works")
        print("✓ STDERR capture works")

        print("\n4. Rejecting an unknown executable...")
        result = run_command(
            repository_root,
            "definitely_not_a_real_command",
        )

        check(
            not result.success,
            "Unknown executable should be rejected.",
        )

        check(
            "not allowed" in (result.error or "").lower(),
            "Expected command allowlist error.",
        )

        print("✓ Unknown executable is rejected")

        print("\n5. Rejecting shell chaining...")
        result = run_command(
            repository_root,
            "python test_script.py && python test_script.py",
        )

        check(
            not result.success,
            "Shell chaining should be rejected.",
        )

        print("✓ Shell chaining is rejected")

        print("\n6. Rejecting PowerShell/cmd execution...")
        result = run_command(
            repository_root,
            "powershell Get-ChildItem",
        )

        check(
            not result.success,
            "PowerShell execution should be rejected.",
        )

        print("✓ PowerShell execution is rejected")

        print("\n7. Timeout handling...")
        timeout_script = repository_root / "timeout_test.py"
        timeout_script.write_text(
            "import time\n"
            "time.sleep(5)\n"
            "print('finished')\n",
            encoding="utf-8",
        )

        result = run_command(
            repository_root,
            "python timeout_test.py",
            timeout=1,
        )

        check(
            not result.success,
            "Timed-out command should fail.",
        )

        check(
            result.metadata.get("timed_out") is True,
            "Timeout metadata was not recorded.",
        )

        check(
            "timed out" in (result.error or "").lower(),
            "Expected timeout error.",
        )

        print("✓ Command timeout handling works")

    print("\n" + "=" * 60)
    print("PHASE 9 TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()