
from typed_envs import EnvVarFactory

envs = EnvVarFactory("EZASYNC")

# We have some envs here to help you debug your custom class implementations

# If you're only interested in debugging a specific class, set this to the class name
DEBUG_CLASS_NAME = envs.create_env("DEBUG_CLASS_NAME", str, default='', verbose=False) 

# Set this to enable debug mode on all classes
DEBUG_MODE = envs.create_env("DEBUG_MODE", bool, default=DEBUG_CLASS_NAME, verbose=False)
