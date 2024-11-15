.. ez-a-sync documentation master file, created by
   sphinx-quickstart on Thu Feb  1 21:29:06 2024.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to ez-a-sync's documentation!
=============================================

ez-a-sync is a big library, but there are only a few things you need to know.

There are two main entrypoints to ez-a-sync, the a_sync decorator and the ASyncGenericBase base class. The vast majority of the other objects in this library support these two entrypoints internally. There is some more you can do, I'll document that stuff later. For now, you have this: 

.. module:: a_sync

.. autodecorator:: a_sync.a_sync

.. autoclass:: a_sync.ASyncGenericBase
   :members:


Those objects will work for most use cases. If you need to do some iteration, the `a_sync.iter` submodule has what you need:

.. automodule:: a_sync.iter
   :members:


There's this cool future class that doesn't interact with the rest of the lib but, depending on your needs, might be even better. WIP:

.. module:: a_sync.future
   .. autodecorator:: a_sync.future.future

   .. autoclass:: a_sync.future.ASyncFuture


Everything else in ez-a-sync can be found by navigating the tree below. Enjoy!

.. toctree::
   :maxdepth: 3
   :caption: Contents:

   source/modules.rst

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
