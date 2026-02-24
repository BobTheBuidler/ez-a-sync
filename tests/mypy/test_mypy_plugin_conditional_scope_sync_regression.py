from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_mypy(tmp_path: Path, code: str) -> str:
    source = tmp_path / "snippet.py"
    source.write_text(dedent(code))
    cache_dir = tmp_path / ".mypy_cache"
    env = dict(os.environ)
    env["MYPY_CACHE_DIR"] = str(cache_dir)
    result = subprocess.run(
        [sys.executable, "-m", "mypy", str(source)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
    )
    output = (result.stdout or "") + (result.stderr or "")
    assert "INTERNAL ERROR" not in output
    assert "Traceback (most recent call last)" not in output
    return output


def test_a_sync_decorator_sync_literal_in_conditional_scope_no_internal_error(
    tmp_path: Path,
) -> None:
    output = _run_mypy(
        tmp_path,
        """
        from a_sync import a_sync

        if a_sync:  # type: ignore[truthy-function]
            @a_sync("sync")
            async def fn(value: int) -> int:
                return value

            reveal_type(fn)
        """,
    )
    assert "Revealed type is" in output
