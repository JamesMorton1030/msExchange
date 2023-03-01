"""The apps module contains all of the application classes and related
tasks which the client can utilise. All apps and tasks should inherit
form the ``BaseApp`` and ``BaseTask`` classes found in the package init
file.
"""

from core.logger import SUSLogger
from abc import ABC, abstractmethod

from utils.timer import Timer

class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

class BaseApp(ABC):
    """The base class for applications which are handled by the client.
    Each application should represent a single running instance of the
    program on the host machine.
    """

    def __init__(self, client):
        self.client = client
        self.activity_logger = SUSLogger(self.client, "application." + self.__class__.__name__, log_type="activity")
        self.debug_logger = SUSLogger(self.client, "application." + self.__class__.__name__, log_type="debug")
        self.app = None

    @abstractmethod
    def open(self):
        """The open method is responsible for opening the application
        and ensuring that it is in a useable state. If the application
        is already open then an object should be returned that relates
        to the open application.
        """

    @abstractmethod
    def close(self):
        """The close method handles the closing of an application and
        should always result in the application being closed. If the
        application is not open then ``False`` should be returned
        otherwise return ``True`` indicating that the application has
        been closed successfully.
        """


class BaseTask(ABC):
    """The base class for all tasks run by the clients scheduling. This
    class is responsible for ensuring all relevant methods are defined
    so that the scheduler works fully.

    The base task supports two key word arguments by default, the first
    *time** should be the amount of seconds that the task should roughly
    run for. A task is welcome to over run but should attempt to keep
    to this time wherever possible. The second property *close_app* is
    used to enforce whether the stop method should close the currently
    used app or keep it open.
    """

    def __init__(self, client, activity_name=None, time=None, close_app=True, **kwargs):
        self.client = client
        self.activity_name = activity_name
        self.close_app = close_app
        self.started = False
        self.app = None

        self.activity_logger = SUSLogger(self.client, "task." + self.__class__.__name__, log_type="activity", module=self.__module__, task=self.__class__.__name__, activity=self.activity_name,)
        self.debug_logger = SUSLogger(self.client, "task." + self.__class__.__name__, log_type="debug", module=self.__module__, task=self.__class__.__name__, activity=self.activity_name,)

        self.timer = Timer(time)

        self.task_load(**kwargs)

    def __str__(self):
        """This method will return the string representation of the task by using the
        class name of the task.
        """
        return self.__class__.__name__
    
    @abstractmethod
    def task_load(self, **kwargs):
        """This method is responsible for ensuring all properties a
        class needs are correctly loaded and set. This includes the
        defining of the ``self.app`` property by requesting an app
        object from the module manager.
        """

    @abstractmethod
    async def main(self):
        """A generator function which contains most the functionality
        of the task. It should yield regularly to allow other tasks to
        run.
        """

    @abstractmethod
    def start(self):
        """This method is called when the task is first started by the
        scheduler. In the process the app will be marked as started and
        the timer object will also be started.
        """
        # This function must be called via super.start() inside the task implementation's start()
        # so the start of the task is logged.
        self.activity_logger.info("Task started", state="START", time_allocated="{} seconds".format(self.timer.total_time))
        self.started = True
        self.timer.start()

    @abstractmethod
    def stop(self):
        """The stop method is called after the main loop of a task has
        finished and should be utilised to restore the application to a
        state which any other task can interact with. If the property
        ``self.close_app`` is True then the app should be closed at
        this point.
        """
        # This function must be called via super().stop() inside task implementation's stop() so
        # end of the task is logged and the app is closed if it needs to be.
        self.activity_logger.info("Task ended", state="END")

        # If self.close_app is set, we need to call close() on the app
        if self.close_app:
            self.app.close()

    def switch_out(self):
        """This method is only called by the scheduler if another task
        has been added in front of this one triggering an interupt. At
        this point the task should make sure it is in a state that can
        be switched away from.
        """
        self.timer.pause()

    def switch_in(self):
        """This method is called when switching back to a running task
        and is designed to allow the task to restore the state it was
        in before it was switched out.
        """
        self.timer.unpause()
