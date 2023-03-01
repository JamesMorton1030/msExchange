"""This module contains the application manager which is responsible
for managing the applications which are accessible by the client.
"""

from importlib.util import find_spec, module_from_spec
from sys import modules as sys_modules

class ModuleManager:
    """The module manager is responsible for processing available apps
    and tasks from each module, dynamically loading any when they are
    needed by the client.
    """

    def __init__(self, config):
        self.modules = {}

        for module in config:
            self.add_module(module)

    def add_module(self, name):
        """This method is used to add a module to the module manager. These are
        then used to dynamically load only the apps and tasks which are
        needed by the client.
        """
        if name in self.modules:
            raise ValueError(f"Module: {name} already loaded")

        spec = find_spec(name)
        if spec is None:
            raise NameError(f"Module: {name} not found")
        module = module_from_spec(spec)
        sys_modules[name] = module

        try:
            spec.loader.exec_module(module)
        except:
            del sys_modules[name]
            raise

        self.modules[name] = {
            "module": module,
            "apps": getattr(module, "APPS", []),
            "tasks": getattr(module, "TASKS", []),
        }

    def get_app(self, module, name, default=None):
        """This function takes an application *name* attempts to load
        the corresponding object from module *module*. 
        if the module does not exist then the *default* value will be returned.
        """

        module = self.modules.get(module)
        if not module or name not in module["apps"]:
            return default
        return getattr(module["module"], name)

    def get_task(self, module, name, default=None):
        """This function takes a task and *name* attempts to load the
        corresponding object from module *module*. 
        if the module does not exist then the *default* value will be returned.
        """
        module = self.modules.get(module)
        if not module or name not in module["tasks"]:
            return default
        return getattr(module["module"], name)

