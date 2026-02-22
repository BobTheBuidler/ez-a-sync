from __future__ import annotations

import os
import subprocess
import sys
from collections import Counter
from pathlib import Path
from textwrap import dedent

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_mypy(
    tmp_path: Path,
    code: str,
    *,
    env_overrides: dict[str, str | None] | None = None,
) -> str:
    source = tmp_path / "snippet.py"
    source.write_text(dedent(code))
    cache_dir = tmp_path / ".mypy_cache"
    env = dict(os.environ)
    env["MYPY_CACHE_DIR"] = str(cache_dir)
    if env_overrides:
        for key, value in env_overrides.items():
            if value is None:
                env.pop(key, None)
            else:
                env[key] = value
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


def _revealed_sequence(output: str) -> list[str]:
    revealed: list[str] = []
    for line in output.splitlines():
        if "Revealed type is" in line:
            revealed.append(line.split("Revealed type is", 1)[1].strip())
    return revealed


def _assert_revealed_contains(output: str, *fragments: str) -> None:
    revealed = _revealed_sequence(output)
    for fragment in fragments:
        assert any(fragment in typ for typ in revealed), (fragment, revealed)


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


def test_proxy_and_future_missing_attribute_errors(tmp_path: Path) -> None:
    output = _run_mypy(
        tmp_path,
        """
        from a_sync.async_property.proxy import AwaitableProxy, ObjectProxy
        from a_sync.future import ASyncFuture

        class Thing:
            def __init__(self) -> None:
                self.count = 1

        thing = Thing()

        obj: ObjectProxy[Thing] = ObjectProxy(thing)
        awaitable: AwaitableProxy[Thing] = AwaitableProxy(thing)
        future: ASyncFuture[Thing]

        reveal_type(obj.count)
        reveal_type(awaitable.count)
        reveal_type(future.count)

        obj.missing
        awaitable.missing
        future.missing
        """,
    )
    expected = Counter(
        [
            '"builtins.int"',
            '"builtins.int"',
            '"builtins.int"',
        ]
    )
    assert _reveal_types(output) == expected
    assert output.count('"Thing" has no attribute') == 3
    assert "obj.missing" in output
    assert "awaitable.missing" in output
    assert "future.missing" in output


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


def test_a_sync_decorator_default_resolution(tmp_path: Path) -> None:
    snippet = """
        from a_sync.a_sync.decorator import a_sync

        sync_deco = a_sync("sync")
        async_deco = a_sync("async")
        neutral_deco = a_sync()

        @a_sync
        async def inferred(value: int) -> int:
            return value

        reveal_type(sync_deco)
        reveal_type(async_deco)
        reveal_type(neutral_deco)
        reveal_type(inferred)
    """
    output = _run_mypy(tmp_path, snippet)
    assert _revealed_sequence(output) == [
        '"a_sync.a_sync.function.ASyncDecoratorSyncDefault"',
        '"a_sync.a_sync.function.ASyncDecoratorAsyncDefault"',
        '"a_sync.a_sync.function.ASyncDecorator"',
        '"a_sync.a_sync.function.ASyncFunctionAsyncDefault[[value: builtins.int], builtins.int]"',
    ]

    # Keep env wiring covered for semantic runs that depend on process env.
    sync_output = _run_mypy(
        tmp_path,
        snippet,
        env_overrides={"A_SYNC_DEFAULT_MODE": "sync"},
    )
    async_output = _run_mypy(
        tmp_path,
        snippet,
        env_overrides={"A_SYNC_DEFAULT_MODE": "async"},
    )
    sync_revealed = _revealed_sequence(sync_output)
    async_revealed = _revealed_sequence(async_output)
    assert sync_revealed[0] == '"a_sync.a_sync.function.ASyncDecoratorSyncDefault"'
    assert sync_revealed[1] == '"a_sync.a_sync.function.ASyncDecoratorAsyncDefault"'
    assert sync_revealed[3] == '"a_sync.a_sync.function.ASyncFunctionAsyncDefault[[value: builtins.int], builtins.int]"'
    assert sync_revealed[2] in {
        '"a_sync.a_sync.function.ASyncDecorator"',
        '"a_sync.a_sync.function.ASyncDecoratorSyncDefault"',
    }
    assert async_revealed[0] == '"a_sync.a_sync.function.ASyncDecoratorSyncDefault"'
    assert async_revealed[1] == '"a_sync.a_sync.function.ASyncDecoratorAsyncDefault"'
    assert async_revealed[3] == '"a_sync.a_sync.function.ASyncFunctionAsyncDefault[[value: builtins.int], builtins.int]"'
    assert async_revealed[2] in {
        '"a_sync.a_sync.function.ASyncDecorator"',
        '"a_sync.a_sync.function.ASyncDecoratorAsyncDefault"',
    }


def test_flag_conflict_hook_reports_error(tmp_path: Path) -> None:
    output = _run_mypy(
        tmp_path,
        """
        from a_sync.a_sync.base import ASyncGenericBase
        from a_sync import a_sync

        class Thing(ASyncGenericBase):
            @a_sync("sync")
            async def compute(self, value: int) -> int:
                return value

        thing = Thing()
        thing.compute(1, sync=True, asynchronous=True)
        """,
    )
    assert "Too many flags: pass at most one of" in output
    assert "'sync' or 'asynchronous'" in output


def test_metaclass_wraps_sync_methods_and_descriptors(tmp_path: Path) -> None:
    output = _run_mypy(
        tmp_path,
        """
        from a_sync.a_sync._meta import ASyncMeta
        from a_sync.a_sync.property import a_sync_property, a_sync_cached_property

        class Thing(metaclass=ASyncMeta):
            def compute(self, value: int) -> int:
                return value

            @a_sync_property
            def value(self) -> int:
                return 1

            @a_sync_cached_property
            def cached(self) -> int:
                return 2

        reveal_type(Thing.compute)
        reveal_type(Thing().compute)
        reveal_type(Thing.value)
        reveal_type(Thing.cached)
        reveal_type(Thing().value)
        reveal_type(Thing().cached)
        """,
    )
    _assert_revealed_contains(
        output,
        "ASyncMethodDescriptor[",
        "ASyncBoundMethod[",
        "ASyncPropertyDescriptor[",
        "ASyncCachedPropertyDescriptor[",
    )
    assert _reveal_types(output)['"typing.Awaitable[int?]"'] == 2


def test_async_generator_descriptor_typing(tmp_path: Path) -> None:
    output = _run_mypy(
        tmp_path,
        """
        from typing import AsyncGenerator
        from a_sync.iter import ASyncGeneratorFunction

        class Thing:
            @ASyncGeneratorFunction
            async def stream(self, value: int) -> AsyncGenerator[int, None]:
                yield value

        reveal_type(Thing.stream)
        reveal_type(Thing().stream)
        """,
    )
    _assert_revealed_contains(output, "ASyncGeneratorFunction[[")
    revealed = _revealed_sequence(output)
    assert len(revealed) == 2
    assert revealed[0] == revealed[1]


def test_a_sync_decorator_in_conditional_scope_does_not_internal_error(tmp_path: Path) -> None:
    output = _run_mypy(
        tmp_path,
        """
        from a_sync import a_sync

        if a_sync:  # type: ignore[truthy-function]
            @a_sync("async")
            async def fn(value: int) -> int:
                return value

            reveal_type(fn)
        """,
    )
    assert "Revealed type is" in output
