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


def _revealed_sequence(output: str) -> list[str]:
    revealed: list[str] = []
    for line in output.splitlines():
        if "Revealed type is" in line:
            revealed.append(line.split("Revealed type is", 1)[1].strip())
    return revealed


def test_a_sync_callable_sync_default_syncfn_preserves_signature(tmp_path: Path) -> None:
    output = _run_mypy(
        tmp_path,
        """
        from a_sync.a_sync.decorator import a_sync

        def base(value: int) -> int:
            return value

        wrapped = a_sync(base, default="sync")
        reveal_type(wrapped)
        """,
    )
    assert _revealed_sequence(output) == [
        '"a_sync.a_sync.function.ASyncFunctionSyncDefault[[value: builtins.int], builtins.int]"',
    ]
