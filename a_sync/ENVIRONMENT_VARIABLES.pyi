from typing import final

from typed_envs import EnvironmentVariable, EnvVarFactory


envs: Final[EnvVarFactory]

DEBUG_CLASS_NAME: Final[EnvironmentVariable[str]]
"""The name of the class to debug.

If you're only interested in debugging a specific class, set this to the class name.

Examples:
    To debug a class named `MyClass`, set the environment variable:
    
    .. code-block:: bash

        export EZASYNC_DEBUG_CLASS_NAME=MyClass

See Also:
    :obj:`DEBUG_MODE` for enabling debug mode on all classes.
"""

DEBUG_MODE: Final[EnvironmentVariable[bool]]
"""Enables debug mode on all classes.

Set this environment variable to `True` to enable debug mode on all classes. 
If `DEBUG_CLASS_NAME` is set to a non-empty string, 
`DEBUG_MODE` will default to `True`.

Examples:
    To enable debug mode globally, set the environment variable:

    .. code-block:: bash

        export EZASYNC_DEBUG_MODE=True

    If you have set `DEBUG_CLASS_NAME` to a specific class, `DEBUG_MODE` will 
    automatically be `True` unless `DEBUG_CLASS_NAME` is an empty string.

See Also:
    :obj:`DEBUG_CLASS_NAME` for debugging a specific class.
"""
