from __future__ import annotations

from pathlib import Path

from repository.search import RepositorySearch
from tools.registry import ToolResult


def search_repo(
    repository_root: str | Path,
    query: str,
    case_sensitive: bool = False,
    max_results: int = 100,
) -> ToolResult:
    """
    Search repository file contents.

    Args:
        repository_root:
            Root directory of the repository.

        query:
            Text to search for.

        case_sensitive:
            Whether the search should be case-sensitive.

        max_results:
            Maximum number of matches to return.
    """

    search_engine = RepositorySearch(
        repository_root
    )

    return search_engine.search(
        query,
        case_sensitive=case_sensitive,
        max_results=max_results,
    )