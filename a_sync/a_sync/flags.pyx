"""
This module provides functionality for handling synchronous and asynchronous flags
in the ez-a-sync library.

ez-a-sync uses 'flags' to indicate whether objects or function calls will be synchronous or asynchronous.

You can use any of the provided flags, whichever makes the most sense for your use case.

:obj:`AFFIRMATIVE_FLAGS`: Set of flags indicating synchronous behavior. Currently includes "sync".

:obj:`NEGATIVE_FLAGS`: Set of flags indicating asynchronous behavior. Currently includes "asynchronous".

:obj:`VIABLE_FLAGS`: Set of all valid flags, combining both synchronous and asynchronous indicators.
"""

cdef public set[str] AFFIRMATIVE_FLAGS = {"sync"}
"""Set of flags indicating synchronous behavior.

This set currently contains only the flag "sync", which is used to denote
synchronous operations within the ez-a-sync library.

Examples:
    >>> 'sync' in AFFIRMATIVE_FLAGS
    True

    >>> 'async' in AFFIRMATIVE_FLAGS
    False

See Also:
    :data:`NEGATIVE_FLAGS`: Flags indicating asynchronous behavior.
    :data:`VIABLE_FLAGS`: All valid flags, combining both sync and async indicators.
"""

cdef public set[str] NEGATIVE_FLAGS = {"asynchronous"}
"""Set of flags indicating asynchronous behavior.

This set currently contains only the flag "asynchronous", which is used to denote
asynchronous operations within the ez-a-sync library.

Examples:
    >>> 'asynchronous' in NEGATIVE_FLAGS
    True

    >>> 'sync' in NEGATIVE_FLAGS
    False

See Also:
    :data:`AFFIRMATIVE_FLAGS`: Flags indicating synchronous behavior.
    :data:`VIABLE_FLAGS`: All valid flags, combining both sync and async indicators.
"""

cdef public set[str] VIABLE_FLAGS = AFFIRMATIVE_FLAGS | NEGATIVE_FLAGS
"""Set of all valid flags, combining both synchronous and asynchronous indicators.

The ez-a-sync library uses these flags to indicate whether objects or function
calls will be synchronous or asynchronous. You can use any of the provided flags,
whichever makes the most sense for your use case.

Examples:
    >>> 'sync' in VIABLE_FLAGS
    True

    >>> 'asynchronous' in VIABLE_FLAGS
    True

    >>> 'invalid' in VIABLE_FLAGS
    False

See Also:
    :data:`AFFIRMATIVE_FLAGS`: Flags indicating synchronous behavior.
    :data:`NEGATIVE_FLAGS`: Flags indicating asynchronous behavior.
"""
