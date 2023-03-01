"""This module contains the application manager which is responsible
for managing the applications which are accessible by the client.
"""
from core.logger import SUSLogger
from selenium import webdriver
from msedge.selenium_tools import Edge
try:
    import pywinauto
except ModuleNotFoundError:
    # pywinauto does not support Linux
    pass

# Currently can only track one instance of each application
# Could also consider adding application config to the get function
class ApplicationManager:
    """The application manager handles the loading of apps from modules
    and also keeps track of all Application objects which the client is
    using.
    """

    def __init__(self, client): #, client, config):
        self.client = client
        self.applications = {}
        self.logger = SUSLogger(client, "client.app_manager", log_type="debug")
        #self.modules = {}
        #self.loaded = {}

        #for module in config:
            #self.add_module(module)

    def __getitem__(self, app_name):
        return self.get(app_name)

    def is_open(self, app_name):
        """Checks if an application is currently open
        Returns True if it is open and False if not
        """
        if app_name in self.applications:
            self.logger.debug(f"{app_name} is open")
            return True
        
        self.logger.debug(f"{app_name} is not open")
        return False

    def add(self, app_name, app_object):
        """Adds an application to the application manager
        """
        self.logger.info(f"Adding application {app_name} to app manager: {app_object}")

        # display a warning if an unexpected object type is added to the app manager
        allowed_objects = [webdriver.Chrome, webdriver.Firefox, webdriver.Edge, Edge]

        # Check that pywinauto is installed
        try:
            allowed_objects.append(pywinauto.Application)
        except NameError:
            pass
        
        # If this object's type is not in the allowed objects, display a warning message
        # TODO: Should this prevent the instance being added rather than a warning?
        if not any(isinstance(app_object, object_type) for object_type in allowed_objects):
            self.logger.warning("An unexpected object type was added to the application manager: {}".format(repr(app_object)))

        self.applications[app_name] = app_object

    def get(self, app_name, default=None):
        """Retrieves a currently opened application if open
        Otherwise return ```default```, this can be overridden
        otherwise will be None
        """
        self.logger.debug(f"Checking whether {app_name} is open.")

        # self.logger.info(self.applications)
        if self.is_open(app_name):
            self.logger.debug(f"Returning {app_name} object as it is open.")
            return self.applications[app_name]

        self.logger.debug(f"App {app_name} did not exist, returning default parameter.")
        return default

    def remove(self, app_name):
        """Removes an app from the application manager
        """
        if self.is_open(app_name):
            del self.applications[app_name]
            return True
        return False

# This looked very similar to modules.py and i couldn't get it to work well with
# the defined schema, I have commented it out so that we can get it back if needed

    # def add_module(self, name):
    #     """This method loads the ``APPS`` list from each of the modules
    #     which tells the manager which apps are in each module.
    #     """
    #     if name in self.modules:
    #         raise ValueError(f"Module: {name} already loaded")
    #     module = import_module(name)
    #     self.modules[name] = module
    #     self.applicatons[name] = getattr(module, "APPS")

    # def get(self, name, default=NULL):
    #     """This method returns an instance of the application object
    #     loading it if necessary. A *default* argument can be included
    #     and if the application cannot be loaded this will be returned.
    #     """
    #     if name in self.loaded:
    #         return self.loaded[name]
    #     for module, apps in self.applicatons.items():
    #         if name in apps:
    #             app = getattr(self.modules[module], name)(self.client)
    #             self.loaded[name] = app
    #             return app
    #     if default is NULL:
    #         raise ValueError(f"No app called: {name}")
    #     return default

    # def close_all(self):
    #     """This method should ensure that all applications are in a
    #     closed state by calling each classes close method.
    #     """
    #     for app in self.loaded.values():
    #         app.close()
