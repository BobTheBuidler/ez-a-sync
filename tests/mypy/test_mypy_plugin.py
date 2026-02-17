from __future__ import annotations

import os
import subprocess
import sys
from collections import Counter
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


def _reveal_types(output: str) -> Counter[str]:
    revealed: list[str] = []
    for line in output.splitlines():
        if "Revealed type is" in line:
            revealed.append(line.split("Revealed type is", 1)[1].strip())
    return Counter(revealed)


def test_proxy_and_future_attribute_typing(tmp_path: Path) -> None:
    output = _run_mypy(
        tmp_path,
        """
        from a_sync.async_property.proxy import AwaitableProxy, ObjectProxy
        from a_sync.future import ASyncFuture

        class Thing:
            def __init__(self) -> None:
                self.count = 1
                self.name = "hey"

        thing = Thing()

        obj: ObjectProxy[Thing] = ObjectProxy(thing)
        awaitable: AwaitableProxy[Thing] = AwaitableProxy(thing)
        future: ASyncFuture[Thing]

        reveal_type(obj.count)
        reveal_type(obj.name)
        reveal_type(awaitable.count)
        reveal_type(awaitable.name)
        reveal_type(future.count)
        reveal_type(future.name)
        """,
    )
    expected = Counter(
        [
            '"builtins.int"',
            '"builtins.str"',
            '"builtins.int"',
            '"builtins.str"',
            '"builtins.int"',
            '"builtins.str"',
        ]
    )
    assert _reveal_types(output) == expected


def test_property_descriptor_typing(tmp_path: Path) -> None:
    output = _run_mypy(
        tmp_path,
        """
        from a_sync.a_sync.base import ASyncGenericBase
        from a_sync.a_sync.property import a_sync_property

        class Thing(ASyncGenericBase):
            @a_sync_property
            def value(self) -> int:
                return 1

        reveal_type(Thing().value)
        """,
    )
    expected = Counter(['"typing.Awaitable[builtins.int]"'])
    assert _reveal_types(output) == expected
