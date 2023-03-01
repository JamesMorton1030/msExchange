"""This module contains the timer class which can be used to keep track
of how much time has elapsed at any time.
"""

from time import time

class Timer:
    """A timer class keeps track of the amount of time that has passed
    since it was started. When evaluating the timer as a bool, it will 
    return true when the timer has finished.
    """

    def __init__(self, total_time):
        # Stores how long the timer should run for
        self.total_time = total_time
        # Stores the total elapsed time since the last pause
        self.__elapsed_time = 0
        # Started time stores the timer was started (or unpaused)
        self.started_time = 0
        self.paused = True

    def __bool__(self):
        return self.time_remaining <= 0
    
    @property
    def time_remaining(self):
        """This property retruns the amount of seconds left
        """
        # We use time_elapsed and not __time_elapsed as we need to consider whether we're paused or not
        return self.total_time - self.time_elapsed
    @property
    def time_elapsed(self):
        """This property returns the amount of seconds elapsed
        """
        # If we're paused, __elapsed_time contains the correct elapsed time
        if self.paused:
            return self.__elapsed_time
        else:
            # Otherwise, we need to take __elapsed_time and add the current time delta since the pause
            return self.__elapsed_time + (time() - self.started_time)

    def start(self):
        """This method starts the timer and resets any stored values so
        that the timer is in a fresh state.
        """
        # Store the current unix time in time_started
        self.started_time = time()
        self.paused = False

    def pause(self):
        """This method stops the timer counting down.
        """
        # Set the remaining time to the current time minus the time it was started
        self.__elapsed_time += time() - self.started_time
        self.paused = True

    def unpause(self):
        """This will start timing again after a pause. Recording the
        time at which the pause started.
        """
        # Set the time_started to the current time
        self.started_time = time()
        self.paused = False