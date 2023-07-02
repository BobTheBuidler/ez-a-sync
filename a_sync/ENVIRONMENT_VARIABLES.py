
import os

# We have some envs here to help you debug your custom class implementations
# If you're only interested in debugging a specific class, set this to the class name
DEBUG_CLASS_NAME = os.environ.get("EZASYNC_DEBUG_CLASS_NAME") 
# Set this to enable debug mode on all classes
DEBUG_MODE = bool(os.environ.get("EZASYNC_DEBUG_MODE", DEBUG_CLASS_NAME))
