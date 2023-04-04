## Table of Contents
<!-- TOC -->

- [Table of Contents](#table-of-contents)
- [Introduction](#introduction)
- [Installation](#installation)
- [Usage](#usage)
    - [Decorators](#decorators)
        - [@a_sync'async'](#a_syncasync)
        - [@a_sync'sync'](#a_syncsync)
    - [Classes](#classes)
    - [Modifiers](#modifiers)
        - [async modifiers](#async-modifiers)
        - [sync modifiers](#sync-modifiers)
        - [Default Modifiers](#default-modifiers)

<!-- /TOC -->
## Introduction

`ez-a-sync` is a Python library that enables developers to write both synchronous and asynchronous code without having to write redundant code. It provides a decorator `@a_sync()`, as well as a base class `ASyncGenericBase` which can be used to create classes that can be executed in both synchronous and asynchronous contexts.

## Installation

`ez-a-sync` can be installed via pip:

```
pip install ez-a-sync
```

## Usage

### Decorators

`ez-a-sync` provides one decorator: `@a_sync()`. You can explicitly pass the type of function you want with `@a_sync('sync')` or `@a_sync('async')`

#### `@a_sync('async')`

The `@a_sync('async')` decorator can be used to define an asynchronous function that can also be executed synchronously.

```python
@a_sync('async')
def some_function():
    ...
```

This function can then be executed asynchronously using `await`:

```python
aaa = await some_function()
```

It can also be executed synchronously by passing `sync=True` or `asynchronous=False`:

```python
aaa = some_function(sync=True)
```

#### `@a_sync('sync')`

The `@a_sync('sync')` decorator can be used to define a synchronous function that can also be executed asynchronously.

```python
@a_sync('sync')
async def some_function():
    ...
```

This function can then be executed synchronously:

```python
aaa = some_function()
```

It can also be overridden asynchronously by passing `sync=False` or `asynchronous=True` and using `await`:

```python
aaa = await some_function(sync=False)
```

### Classes

`ez-a-sync` also provides a base class `ASyncGenericBase` that can be used to create classes that can be executed in both synchronous and asynchronous contexts. To create an asynchronous class, simply inherit from `ASyncGenericBase` and set `asynchronous=True`:

```python
class CoolAsyncClass(ASyncGenericBase):
    asynchronous=True
    
    def some_sync_fn():
       ...   
```

In this example, `CoolAsyncClass` has `asynchronous=True`, which means it is an asynchronous class. You can call `some_sync_fn` asynchronously using `await`:

```python
aaa = await CoolAsyncClass().some_sync_fn()
```

`CoolAsyncClass` functions can also be called synchronously by passing `sync=True`:

```python
aaa = CoolAsyncClass().some_sync_fn(sync=True)
```

Similarly, you can create a synchronous class by setting `sync=True` or `asynchronous=False`:

```python
class CoolSyncClass(ASyncGenericBase):
    asynchronous=False
    
    async def some_async_fn():
       ...
```

`CoolSyncClass` functions can be called synchronously:

```python
aaa = CoolSyncClass().some_async_fn()
```

It can also be called asynchronously by passing `sync=False` or `asynchronous=True` and using `await`:

```python
aaa = await CoolSyncClass().some_async_fn(sync=False)
```

You can also create a class which functions can be executed in both synchronous and asynchronous contexts by not setting the `asynchronous` or `sync` attribute (both can be used interchangeably, pick your favorite) and passing it as an argument when creating an instance:

```python
class CoolDualClass(ASyncGenericBase):
    def __init__(self, asynchronous):
        self.asynchronous=asynchronous
    
    async def some_async_fn():
       ...
```

You can create an instance of `CoolDualClass` with `sync=False` or `asynchronous=True` to call it asynchronously:

```python
async_instance = CoolDualClass(asynchronous=True)
aaa = await async_instance.some_async_fn()
aaa = async_instance.some_async_fn(sync=True)
```

You can also create an instance with `sync=True` or `asynchronous=False` to call it synchronously:

```python
sync_instance = CoolDualClass(asynchronous=False)
aaa = sync_instance.some_async_fn()
aaa = sync_instance.some_async_fn(sync=False)
```

### Modifiers

The `ez-a-sync` library provides several settings that can be used to customize the behavior of the decorators and classes.

To apply settings to the decorators or base classes, simply pass them as keyword arguments when calling the decorator or creating an instance.

For example, to apply `cache_type='memory'` to a function decorated with `@a_sync('async')`, you would do the following:

```python
@a_sync('async', cache_type='memory')
def some_function():
    ...
```

#### async modifiers

The `@a_sync('async')` decorator has the following settings:

- `cache_type`: This can be set to `None` or `'memory'`. `'memory'` is a LRU cache which can be modified with the `cache_typed`, `ram_cache_maxsize`, and `ram_cache_ttl` modifiers.
- `cache_typed`: Set to `True` if you want types considered treated for cache keys. i.e. with `cache_typed=True`, `Decimal(0)` and `0` will be considered separate keys.
- `ram_cache_maxsize`: The maxsize for your LRU cache. Set to `None` if the cache is unbounded. If you set this value without specifying a cache type, `'memory'` will automatically be applied.
- `ram_cache_ttl`: The TTL for items in your LRU cache. Set to `None`. If you set this value without specifying a cache type, `'memory'` will automatically be applied.
- `runs_per_minute`: Setting this value enables a rate limiter for the decorated function.
- `semaphore`: Drop in a Semaphore for your async defined functions.

#### sync modifiers

The `@a_sync('sync')` decorator has the following setting:

- `executor`: The executor for the synchronous function. Set to the library's default of `config.default_sync_executor`.

#### Default Modifiers

Instead of setting modifiers one by one in functions, you can set a default value for modifiers using ENV variables:

- `DEFAULT_MODE`
- `CACHE_TYPE`
- `CACHE_TYPED`
- `RAM_CACHE_MAXSIZE`
- `RAM_CACHE_TTL`
- `RUNS_PER_MINUTE`
- `SEMAPHORE`
