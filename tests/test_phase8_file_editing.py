from __future__ import annotations

import tempfile
from pathlib import Path

from tools.filesystem import edit_file, read_file, write_file


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    print("=" * 60)
    print("PHASE 8 — FILE EDITING TEST")
    print("=" * 60)

    with tempfile.TemporaryDirectory(prefix="phase8_repo_") as temp_dir:
        repository_root = Path(temp_dir)

        print("\n1. Creating a new file...")
        result = write_file(
            repository_root,
            "src/example.py",
            "def hello():\n    return 'hello'\n",
        )

        check(
            result.success,
            result.error or "write_file failed",
        )

        created_file = repository_root / "src" / "example.py"

        check(
            created_file.exists(),
            "File was not created.",
        )

        check(
            created_file.is_file(),
            "Created path is not a file.",
        )

        print("✓ File creation works")

        print("\n2. Preventing accidental overwrite...")
        result = write_file(
            repository_root,
            "src/example.py",
            "replacement\n",
        )

        check(
            not result.success,
            "Existing file was overwritten without permission.",
        )

        check(
            "already exists" in (result.error or ""),
            "Expected overwrite protection error.",
        )

        print("✓ Overwrite protection works")

        print("\n3. Editing one exact text block...")
        result = edit_file(
            repository_root,
            "src/example.py",
            "def hello():\n    return 'hello'",
            "def hello(name='world'):\n    return f'hello {name}'",
        )

        check(
            result.success,
            result.error or "edit_file failed",
        )

        updated_content = created_file.read_text(
            encoding="utf-8",
        )

        check(
            "def hello(name='world'):" in updated_content,
            "Updated function definition was not found.",
        )

        check(
            "return f'hello {name}'" in updated_content,
            "Updated return statement was not found.",
        )

        check(
            "def hello():\n    return 'hello'" not in updated_content,
            "Old text still exists after edit.",
        )

        print("✓ Exact replacement works")

        print("\n4. Rejecting ambiguous edits...")

        ambiguous_file = repository_root / "ambiguous.txt"

        ambiguous_file.write_text(
            "value = 10\n"
            "print(value)\n"
            "value = 10\n",
            encoding="utf-8",
        )

        result = edit_file(
            repository_root,
            "ambiguous.txt",
            "value = 10",
            "value = 20",
        )

        check(
            not result.success,
            "Ambiguous edit should have failed.",
        )

        check(
            "occurs 2 times" in (result.error or ""),
            "Expected ambiguous replacement error.",
        )

        print("✓ Ambiguous replacement is rejected")

        print("\n5. Rejecting missing old_text...")
        result = edit_file(
            repository_root,
            "src/example.py",
            "THIS TEXT DOES NOT EXIST",
            "anything",
        )

        check(
            not result.success,
            "Edit with missing old_text should fail.",
        )

        check(
            "not found" in (result.error or ""),
            "Expected missing-text error.",
        )

        print("✓ Missing old_text is rejected")

        print("\n6. Rejecting path traversal...")
        result = write_file(
            repository_root,
            "../outside.txt",
            "blocked",
        )

        check(
            not result.success,
            "Path traversal should have been blocked.",
        )

        outside_file = repository_root.parent / "outside.txt"

        check(
            not outside_file.exists(),
            "Path traversal created a file outside the repository.",
        )

        print("✓ Path traversal protection works")

        print("\n7. Reading the edited file...")
        result = read_file(
            repository_root,
            "src/example.py",
        )

        check(
            result.success,
            result.error or "read_file failed",
        )

        check(
            "def hello(name='world'):" in result.output,
            "Edited function was not found through read_file.",
        )

        check(
            "return f'hello {name}'" in result.output,
            "Edited return statement was not found through read_file.",
        )

        print("✓ read_file sees the edited content")

        print("\n8. Explicit overwrite...")
        result = write_file(
            repository_root,
            "src/example.py",
            "def replacement():\n    return 'replacement'\n",
            overwrite=True,
        )

        check(
            result.success,
            result.error or "Explicit overwrite failed",
        )

        overwritten_content = created_file.read_text(
            encoding="utf-8",
        )

        check(
            "def replacement():" in overwritten_content,
            "Explicit overwrite did not replace the file.",
        )

        check(
            "def hello(name='world'):" not in overwritten_content,
            "Old content remains after overwrite.",
        )

        print("✓ Explicit overwrite works")

    print("\n" + "=" * 60)
    print("PHASE 8 TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()