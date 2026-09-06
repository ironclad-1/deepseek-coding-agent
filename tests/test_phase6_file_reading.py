from __future__ import annotations

from pathlib import Path

from tools.filesystem import read_file


TEST_CONTENT = """Line one
Line two
Line three
Line four
Line five
"""


def main() -> None:
    print("=" * 60)
    print("PHASE 6 — FILE READING TEST")
    print("=" * 60)

    repository_root = (
        Path(__file__).resolve().parents[1]
    )

    test_directory = repository_root / "workspace"

    test_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    test_file = test_directory / "phase6_sample.txt"

    test_file.write_text(
        TEST_CONTENT,
        encoding="utf-8",
    )

    # ---------------------------------------------------------
    # 1. Read complete file
    # ---------------------------------------------------------

    print("\n1. Reading complete file...")

    result = read_file(
        repository_root,
        "workspace/phase6_sample.txt",
    )

    if not result.success:
        raise RuntimeError(result.error)

    print(result.output)
    print("✓ Full file read successfully")

    # ---------------------------------------------------------
    # 2. Read line range
    # ---------------------------------------------------------

    print("\n2. Reading line range 2-4...")

    result = read_file(
        repository_root,
        "workspace/phase6_sample.txt",
        start_line=2,
        end_line=4,
    )

    if not result.success:
        raise RuntimeError(result.error)

    expected = (
        "2: Line two\n"
        "3: Line three\n"
        "4: Line four"
    )

    if result.output != expected:
        raise RuntimeError(
            f"Unexpected line-range result:\n"
            f"{result.output}"
        )

    print(result.output)
    print("✓ Line range works")

    # ---------------------------------------------------------
    # 3. Missing file
    # ---------------------------------------------------------

    print("\n3. Testing missing file...")

    result = read_file(
        repository_root,
        "workspace/does_not_exist.txt",
    )

    if result.success:
        raise RuntimeError(
            "Missing file unexpectedly succeeded."
        )

    print(f"✓ Missing file handled: {result.error}")

    # ---------------------------------------------------------
    # 4. Directory instead of file
    # ---------------------------------------------------------

    print("\n4. Testing directory path...")

    result = read_file(
        repository_root,
        "workspace",
    )

    if result.success:
        raise RuntimeError(
            "Directory unexpectedly succeeded."
        )

    print(f"✓ Directory handled: {result.error}")

    # ---------------------------------------------------------
    # 5. Path traversal
    # ---------------------------------------------------------

    print("\n5. Testing path traversal protection...")

    result = read_file(
        repository_root,
        "../phase6_outside.txt",
    )

    if result.success:
        raise RuntimeError(
            "Path traversal unexpectedly succeeded."
        )

    print(f"✓ Path traversal blocked: {result.error}")

    # ---------------------------------------------------------
    # 6. Invalid line range
    # ---------------------------------------------------------

    print("\n6. Testing invalid line range...")

    result = read_file(
        repository_root,
        "workspace/phase6_sample.txt",
        start_line=0,
        end_line=2,
    )

    if result.success:
        raise RuntimeError(
            "Invalid line range unexpectedly succeeded."
        )

    print(f"✓ Invalid range handled: {result.error}")

    # ---------------------------------------------------------
    # Cleanup
    # ---------------------------------------------------------

    test_file.unlink(
        missing_ok=True,
    )

    print()
    print("=" * 60)
    print("PHASE 6 TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()