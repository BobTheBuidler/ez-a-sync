from typed_envs import EnvVarFactory

envs = EnvVarFactory("EZASYNC")

# We have some envs here to help you debug your custom class implementations

cdef public str DEBUG_CLASS_NAME = str(envs.create_env("DEBUG_CLASS_NAME", str, default="", verbose=False))
"""The name of the class to debug.

If you're only interested in debugging a specific class, set this to the class name.

Examples:
    To debug a class named `MyClass`, set the environment variable:
    
    .. code-block:: bash

        export EZASYNC_DEBUG_CLASS_NAME=MyClass

See Also:
    :obj:`DEBUG_MODE` for enabling debug mode on all classes.
"""

cdef public bint DEBUG_MODE = bool(envs.create_env("DEBUG_MODE", bool, default=bool(DEBUG_CLASS_NAME), verbose=False))
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
