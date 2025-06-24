"""Sphinx documentation plugin used to document ASyncFunction, ASyncDescriptor, and ASyncGeneratorFunction instances.

This extension requires Sphinx 2.0 or later. It automatically finds ASyncFunction objects, ASyncDescriptor objects, and ASyncGeneratorFunction objects (e.g. when using the automodule directive) and generates documentation with standardized prefixes.

To enable this extension, add it to your :file:`docs/conf.py` configuration file:

    extensions = (
        ...,
        'a_sync.sphinx.ext',
    )

You can customize the prefixes used in the reference documentation by setting the following configuration values in your Sphinx configuration:

    a_sync_function_prefix = "ASyncFunction"              # Default prefix for dual-function tasks
    a_sync_function_sync_prefix = "ASyncFunction (sync)"    # Prefix for tasks with synchronous default
    a_sync_function_async_prefix = "ASyncFunction (async)"  # Prefix for tasks with asynchronous default
    a_sync_descriptor_prefix = "ASyncDescriptor"            # Default prefix for descriptors
    a_sync_generator_function_prefix = "ASyncGeneratorFunction"  # Default prefix for generator functions

Example:
    In your Sphinx configuration, you could override the default prefixes as follows:

    .. code-block:: python

        a_sync_function_prefix = "CustomFunction"
        a_sync_descriptor_prefix = "CustomDescriptor"
        a_sync_generator_function_prefix = "CustomGenFunction"

See Also:
    :class:`~a_sync.a_sync.function.ASyncFunction`
    :class:`~a_sync.a_sync._descriptor.ASyncDescriptor`
    :class:`~a_sync.a_sync.iter.ASyncGeneratorFunction`
"""

from inspect import signature

from docutils import nodes
from sphinx.domains.python import PyFunction, PyMethod
from sphinx.ext.autodoc import FunctionDocumenter, MethodDocumenter

from a_sync.a_sync._descriptor import ASyncDescriptor
from a_sync.a_sync.function import (
    ASyncFunction,
    ASyncFunctionAsyncDefault,
    ASyncFunctionSyncDefault,
)
from a_sync.iter import ASyncGeneratorFunction


class _ASyncWrapperDocumenter:
    """Base class for documenters that handle wrapped ASync functions.

    This class provides helper methods to check if a member can be documented
    as a dual-mode function by verifying that it is an instance of a specific type
    and that it wraps another callable object.

    Example:
        >>> if _ASyncWrapperDocumenter.can_document_member(member, 'name', False, parent):
        ...     # Proceed with documentation of the member
        ...     pass

    See Also:
        :class:`~a_sync.a_sync.function.ASyncFunction`
    """

    typ: type

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):
        """Determine if the member can be documented by this documenter.

        Args:
            member: The member to check.
            membername: The name of the member.
            isattr: Boolean indicating if the member is an attribute.
            parent: The parent object.

        Returns:
            bool: True if the member can be documented, False otherwise.
        """
        return isinstance(member, cls.typ) and getattr(member, "__wrapped__") is not None

    def document_members(self, all_members=False):
        """Document members of the object.

        Args:
            all_members: Boolean indicating if all members should be documented.
        """
        pass

    def check_module(self):
        """Check if the object is defined in the expected module.

        Returns:
            bool: True if the object is defined in the expected module, False otherwise.

        Note:
            Normally, this checks if *self.object* is defined in the module
            given by *self.modname*. For functions decorated with the task decorator,
            the descriptor holds the wrapped function and this method ensures that
            the wrapped function is used for the module check.
        """
        wrapped = getattr(self.object, "__wrapped__", None)
        if wrapped and getattr(wrapped, "__module__") == self.modname:
            return True
        return super().check_module()


class _ASyncFunctionDocumenter(_ASyncWrapperDocumenter, FunctionDocumenter):
    """Documenter for ASyncFunction instances.

    This documenter formats the arguments of the wrapped function by inspecting
    the signature of the original callable.

    Example:
        Given a function decorated with @a_sync('async'), this documenter
        will generate its signature for the autodoc documentation.
        
    See Also:
        :class:`~a_sync.a_sync.function.ASyncFunction`
    """

    def format_args(self):
        """Format the arguments of the wrapped function.

        Returns:
            str: The formatted arguments.
        """
        wrapped = getattr(self.object, "__wrapped__", None)
        if wrapped is not None:
            sig = signature(wrapped)
            if "self" in sig.parameters or "cls" in sig.parameters:
                sig = sig.replace(parameters=list(sig.parameters.values())[1:])
            return str(sig)
        return ""


class _ASyncMethodDocumenter(_ASyncWrapperDocumenter, MethodDocumenter):
    """Documenter for ASyncMethod instances.

    This documenter formats the arguments of the wrapped method by using the signature
    of the original callable.

    See Also:
        :class:`~a_sync.a_sync.function.ASyncFunction`
    """

    def format_args(self):
        """Format the arguments of the wrapped method.

        Returns:
            str: The formatted arguments.
        """
        wrapped = getattr(self.object, "__wrapped__")
        if wrapped is not None:
            return str(signature(wrapped))
        return ""


class _ASyncDirective:
    """Base class for ASync directives.

    Provides common functionality for generating a signature prefix
    from Sphinx configuration values.
    """

    prefix_env: str

    def get_signature_prefix(self, sig):
        """Get the signature prefix for the directive.

        Args:
            sig: The signature to process.

        Returns:
            list: A list of nodes representing the signature prefix.

        Example:
            This method returns nodes such as :obj:`nodes.Text(...)`
            with the prefix read from Sphinx configuration.
        """
        return [nodes.Text(getattr(self.env.config, self.prefix_env))]


class _ASyncFunctionDirective(_ASyncDirective, PyFunction):
    """Directive for ASyncFunction instances.

    This directive uses the prefix defined by the Sphinx configuration
    value :confval:`a_sync_function_prefix`.
    """
    pass


class _ASyncMethodDirective(_ASyncDirective, PyMethod):
    """Directive for ASyncMethod instances.

    This directive uses the prefix defined by the Sphinx configuration
    value :confval:`a_sync_descriptor_prefix`.
    """
    pass


class ASyncFunctionDocumenter(_ASyncFunctionDocumenter):
    """Document ASyncFunction instance definitions.

    This documenter registers itself under the object type ``a_sync_function``
    and uses the default prefix from :confval:`a_sync_function_prefix`.

    Example:
        In the generated documentation, the function will be prefixed with "ASyncFunction".
    """
    objtype = "a_sync_function"
    typ = ASyncFunction
    priority = 15
    # member_order = 11


class ASyncFunctionSyncDocumenter(_ASyncFunctionDocumenter):
    """Document ASyncFunctionSyncDefault instance definitions.

    This documenter registers itself under the object type ``a_sync_function_sync``
    and uses the prefix from :confval:`a_sync_function_sync_prefix`.

    Example:
        A function decorated with @a_sync('sync') will use this documenter and appear with the prefix "ASyncFunction (sync)".
    """
    objtype = "a_sync_function_sync"
    typ = ASyncFunctionSyncDefault
    priority = 14
    # member_order = 11


class ASyncFunctionAsyncDocumenter(_ASyncFunctionDocumenter):
    """Document ASyncFunctionAsyncDefault instance definitions.

    This documenter registers itself under the object type ``a_sync_function_async``
    and uses the prefix from :confval:`a_sync_function_async_prefix`.

    Example:
        A function decorated with @a_sync('async') will use this documenter and appear with the prefix "ASyncFunction (async)".
    """
    objtype = "a_sync_function_async"
    typ = ASyncFunctionAsyncDefault
    priority = 13
    # member_order = 11


class ASyncFunctionDirective(_ASyncFunctionDirective):
    """Directive for ASyncFunction instances.

    Uses the configuration value :confval:`a_sync_function_prefix` as a prefix for the signature.
    """
    prefix_env = "a_sync_function_prefix"


class ASyncFunctionSyncDirective(_ASyncFunctionDirective):
    """Directive for ASyncFunctionSyncDefault instances.

    Uses the configuration value :confval:`a_sync_function_sync_prefix` as a prefix.
    """
    prefix_env = "a_sync_function_sync_prefix"


class ASyncFunctionAsyncDirective(_ASyncFunctionDirective):
    """Directive for ASyncFunctionAsyncDefault instances.

    Uses the configuration value :confval:`a_sync_function_async_prefix` as a prefix.
    """
    prefix_env = "a_sync_function_async_prefix"


class ASyncDescriptorDocumenter(_ASyncMethodDocumenter):
    """Document ASyncDescriptor instance definitions.

    This documenter is used to generate documentation for ASyncDescriptor objects.
    It registers under the type ``a_sync_descriptor`` and uses the appropriate prefix.
    """
    objtype = "a_sync_descriptor"
    typ = ASyncDescriptor
    # member_order = 11


class ASyncDescriptorDirective(_ASyncMethodDirective):
    """Directive for ASyncDescriptor instances.

    Uses the configuration value :confval:`a_sync_descriptor_prefix` to generate prefixes.
    """
    prefix_env = "a_sync_descriptor_prefix"


class ASyncGeneratorFunctionDocumenter(_ASyncFunctionDocumenter):
    """Document ASyncGeneratorFunction instance definitions.

    This documenter registers under the object type ``a_sync_generator_function``
    and uses the prefix from :confval:`a_sync_generator_function_prefix`.

    Example:
        When documenting an async generator function, the signature will be prefixed with "ASyncGeneratorFunction".
    """
    objtype = "a_sync_generator_function"
    typ = ASyncGeneratorFunction
    # member_order = 11


class ASyncGeneratorFunctionDirective(_ASyncFunctionDirective):
    """Directive for ASyncGeneratorFunction instances.

    Uses the configuration value :confval:`a_sync_generator_function_prefix` as its signature prefix.
    """
    prefix_env = "a_sync_generator_function_prefix"


def autodoc_skip_member_handler(app, what, name, obj, skip, options):
    """Handler for autodoc-skip-member event.

    Args:
        app: The Sphinx application object.
        what: The type of the object being documented.
        name: The name of the object.
        obj: The object itself.
        skip: Boolean indicating if the member should be skipped.
        options: The options for the autodoc directive.

    Returns:
        bool: True if the member should be skipped, False otherwise.

    Example:
        This handler ensures that ASyncFunction, ASyncDescriptor, and ASyncGeneratorFunction
        objects with a __wrapped__ attribute are not skipped automatically.
    """
    if isinstance(obj, (ASyncFunction, ASyncDescriptor, ASyncGeneratorFunction)) and getattr(
        obj, "__wrapped__"
    ):
        if skip:
            return False
    return None


def setup(app):
    """Setup Sphinx extension.

    Args:
        app: The Sphinx application object.

    Returns:
        dict: A dictionary with metadata about the extension.

    Example:
        When Sphinx starts, it calls this setup function to register autodocumenters,
        directives, and configuration values for ASync objects.

    Note:
        There is no alternate manual directive (such as ``.. autotask::``) registered by this extension.
    """
    app.setup_extension("sphinx.ext.autodoc")

    # function
    app.add_autodocumenter(ASyncFunctionDocumenter)
    app.add_autodocumenter(ASyncFunctionSyncDocumenter)
    app.add_autodocumenter(ASyncFunctionAsyncDocumenter)
    app.add_directive_to_domain("py", "a_sync_function", ASyncFunctionDirective)
    app.add_directive_to_domain("py", "a_sync_function_sync", ASyncFunctionSyncDirective)
    app.add_directive_to_domain("py", "a_sync_function_async", ASyncFunctionAsyncDirective)
    app.add_config_value("a_sync_function_sync_prefix", "ASyncFunction (sync)", True)
    app.add_config_value("a_sync_function_async_prefix", "ASyncFunction (async)", True)
    app.add_config_value("a_sync_function_prefix", "ASyncFunction", True)

    # descriptor
    app.add_autodocumenter(ASyncDescriptorDocumenter)
    app.add_directive_to_domain("py", "a_sync_descriptor", ASyncDescriptorDirective)
    app.add_config_value("a_sync_descriptor_prefix", "ASyncDescriptor", True)

    # generator
    app.add_autodocumenter(ASyncGeneratorFunctionDocumenter)
    app.add_directive_to_domain("py", "a_sync_generator_function", ASyncGeneratorFunctionDirective)
    app.add_config_value("a_sync_generator_function_prefix", "ASyncGeneratorFunction", True)

    app.connect("autodoc-skip-member", autodoc_skip_member_handler)

    return {"parallel_read_safe": True}