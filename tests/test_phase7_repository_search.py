from __future__ import annotations

from pathlib import Path

from tools.search import search_repo


TEST_CONTENT_1 = """def authenticate_user(username, password):
    validate_credentials(username, password)
    create_session(username)
    return True
"""


TEST_CONTENT_2 = """def validate_credentials(username, password):
    return check_database(username, password)
"""


def main() -> None:
    print("=" * 60)
    print("PHASE 7 — REPOSITORY SEARCH TEST")
    print("=" * 60)

    repository_root = (
        Path(__file__).resolve().parents[1]
    )

    test_directory = (
        repository_root / "workspace" / "phase7_search_test"
    )

    test_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    auth_file = test_directory / "auth.py"
    validation_file = test_directory / "validation.py"

    auth_file.write_text(
        TEST_CONTENT_1,
        encoding="utf-8",
    )

    validation_file.write_text(
        TEST_CONTENT_2,
        encoding="utf-8",
    )

    # ---------------------------------------------------------
    # 1. Basic search
    # ---------------------------------------------------------

    print("\n1. Basic repository search...")

    result = search_repo(
        repository_root,
        "authenticate_user",
    )

    if not result.success:
        raise RuntimeError(result.error)

    print(result.output)

    if "auth.py:1:" not in result.output:
        raise RuntimeError(
            "Expected authenticate_user match was not found."
        )

    print("✓ Basic search works")

    # ---------------------------------------------------------
    # 2. Case-insensitive search
    # ---------------------------------------------------------

    print("\n2. Case-insensitive search...")

    result = search_repo(
        repository_root,
        "AUTHENTICATE_USER",
        case_sensitive=False,
    )

    if not result.success:
        raise RuntimeError(result.error)

    if "auth.py:1:" not in result.output:
        raise RuntimeError(
            "Case-insensitive search failed."
        )

    print("✓ Case-insensitive search works")

    # ---------------------------------------------------------
    # 3. Case-sensitive search
    # ---------------------------------------------------------

    print("\n3. Case-sensitive search...")

    uppercase_query = "AUTH_" + "NO_MATCH_" + "CASE"

    result = search_repo(
        repository_root,
        uppercase_query,
        case_sensitive=True,
    )

    if not result.success:
        raise RuntimeError(result.error)

    if "No matches found" not in result.output:
        raise RuntimeError(
            "Case-sensitive search returned an unexpected match."
        )

    print("✓ Case-sensitive search works")

    # ---------------------------------------------------------
    # 4. Multiple matches
    # ---------------------------------------------------------

    print("\n4. Multiple-match search...")

    result = search_repo(
        repository_root,
        "username",
    )

    if not result.success:
        raise RuntimeError(result.error)

    print(result.output)

    match_count = result.metadata["match_count"]

    if match_count < 2:
        raise RuntimeError(
            "Expected multiple matches."
        )

    print("✓ Multiple matches work")

    # ---------------------------------------------------------
    # 5. Result limit
    # ---------------------------------------------------------

    print("\n5. Result limit...")

    result = search_repo(
        repository_root,
        "username",
        max_results=1,
    )

    if not result.success:
        raise RuntimeError(result.error)

    if result.metadata["match_count"] != 1:
        raise RuntimeError(
            "max_results was not respected."
        )

    print("✓ Result limit works")

    # ---------------------------------------------------------
    # 6. No matches
    # ---------------------------------------------------------

    print("\n6. No-match handling...")

    no_match_query = (
        "STRING_"
        + "THAT_"
        + "WILL_"
        + "NEVER_"
        + "MATCH"
    )

    result = search_repo(
        repository_root,
        no_match_query,
    )

    if not result.success:
        raise RuntimeError(result.error)

    if "No matches found" not in result.output:
        raise RuntimeError(
            "No-match handling failed."
        )

    print("✓ No-match handling works")

    # ---------------------------------------------------------
    # 7. Empty query
    # ---------------------------------------------------------

    print("\n7. Empty-query handling...")

    result = search_repo(
        repository_root,
        "",
    )

    if result.success:
        raise RuntimeError(
            "Empty query unexpectedly succeeded."
        )

    print(
        f"✓ Empty query handled: {result.error}"
    )

    # ---------------------------------------------------------
    # Cleanup
    # ---------------------------------------------------------

    auth_file.unlink(missing_ok=True)
    validation_file.unlink(missing_ok=True)

    try:
        test_directory.rmdir()
        test_directory.parent.rmdir()
    except OSError:
        pass

    print()
    print("=" * 60)
    print("PHASE 7 TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()