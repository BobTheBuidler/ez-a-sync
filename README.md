# ez-a-sync

super lite docs (better coming eventually):

```
@a_sync('async')
def some_function():
    ...
    
aaa = await some_function()      <- this works
aaa = some_function(sync=True)   <- this works
```

```
@a_sync('sync')
async def some_async_fn():
   ...
   
aaa = some_async_fn()                  <- this works
aaa = await some_async_fn(sync=False)  <- this works
```

```
class CoolAsyncClass(ASyncGenericBase):
    asynchronous=True
    
    def some_sync_fn():
       ...   
       
aaa = await CoolAsyncClass().some_sync_fn()
```

```
class CoolSyncClass(ASyncGenericBase):
    asynchronous=False
    
    async def some_async_fn():
       ...
       
       
aaa = CoolSyncClass().some_async_fn()
```

```
class CoolDualClass(ASyncGenericBase):
    def __init__(self, asynchronous):
        self.asynchronous=asynchronous
    
    async def some_async_fn():
       ...
       

async_instance = CoolDualClass(asynchronous=True)
sync_instance = CoolDualClass(asynchronous=False)

aaa = await async_instance.some_async_fn()
aaa = async_instance.some_async_fn(sync=True)

aaa = sync_instance.some_async_fn()
aaa = sync_instance.some_async_fn(sync=False)
```

