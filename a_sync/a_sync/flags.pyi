"""
This module provides functionality for handling synchronous and asynchronous flags in the ez-a-sync library.

The ez‐a‐sync library uses flags to indicate whether objects or function calls operate synchronously or asynchronously. You can use any of the provided flags, whichever best fits your use case.

Attributes:
    AFFIRMATIVE_FLAGS: A set of flags indicating synchronous behavior. Currently, it contains only the string "sync".
    NEGATIVE_FLAGS: A set of flags indicating asynchronous behavior. Currently, it contains only the string "async".
    VIABLE_FLAGS: A set of all valid flags, combining both synchronous and asynchronous indicators.

See Also:
    :data:`AFFIRMATIVE_FLAGS`
    :data:`NEGATIVE_FLAGS`
    :data:`VIABLE_FLAGS`
"""

from typing import Set

AFFIRMATIVE_FLAGS: Set[str]
"""A set of flags that indicate synchronous behavior.

This constant contains only the string "sync" to denote synchronous operations within the ez‐a‐sync library.

Examples:
    >>> 'sync' in AFFIRMATIVE_FLAGS
    True
    >>> 'async' in AFFIRMATIVE_FLAGS
    False

See Also:
    :data:`NEGATIVE_FLAGS`: Flags indicating asynchronous behavior.
    :data:`VIABLE_FLAGS`: Combined set of all valid flags.
"""

NEGATIVE_FLAGS: Set[str]
"""A set of flags that indicate asynchronous behavior.

This constant contains only the string "async" to denote asynchronous operations within the ez‐a‐sync library.

Examples:
    >>> 'async' in NEGATIVE_FLAGS
    True
    >>> 'sync' in NEGATIVE_FLAGS
    False

See Also:
    :data:`AFFIRMATIVE_FLAGS`: Flags indicating synchronous behavior.
    :data:`VIABLE_FLAGS`: Combined set of all valid flags.
"""

VIABLE_FLAGS: Set[str]
"""A set containing all valid flags for denoting synchronous or asynchronous behavior.

This constant combines the flags used for both synchronous and asynchronous operations. Currently it includes both "sync" and "async".

Examples:
    >>> 'sync' in VIABLE_FLAGS
    True
    >>> 'async' in VIABLE_FLAGS
    True
    >>> 'invalid' in VIABLE_FLAGS
    False

See Also:
    :data:`AFFIRMATIVE_FLAGS`: Synchronous behavior flags.
    :data:`NEGATIVE_FLAGS`: Asynchronous behavior flags.
"""