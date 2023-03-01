"""This module contains the scheduling system which the client uses to
determine which task it should currently be running.
"""
import traceback
import sys
import math
from utils import select_random
from random import randrange

class Scheduler:
    """The scheduler class is responsible for ensuring that the client
    runs the right task at the right time. It does this using an array
    where the top element is always what is being run.
    """

    def __init__(self, client):
        self.schedule = []
        self.client = client

        self.current_task = None

    async def interrupt(self, interrupt_task):
        """TODO
        """
        # Store our current task
        # We must store this as calling self.run_task will overwrite self.current_task
        current_task = self.current_task
        
        # Switch out of this task
        current_task.switch_out()

        # Run the new task
        await self.run_task(interrupt_task)

        # Switch back into this task
        current_task.switch_in()

    async def run_task(self, task):
        """TODO
        """
        # Store our task we're currently running
        self.current_task = task

        # Run the task
        try:
            # Start our task
            self.current_task.start()

            # Run the task's main function
            await task.main()

            # Once it's finished, run the stop function
            task.stop()
        except Exception as _:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            exception_stacktrace = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))

            # Now log the stack trace in debug log
            self.client.logger.error(f"Task {str(task)} has raised an exception: {exception_stacktrace}")

            # Check whether development mode is enabled and if so, raise exception as normal after logging the error
            if self.client.config["development_mode"]:
                # Raise exception as usual
                raise
            else:
                # Stop the current task as it's crashed
                # TODO: Should we force close the app?
                try:
                    task.close_app = True
                    task.stop()
                except Exception as _:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    exception_stacktrace = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))

                    # Now log the stack trace in debug log
                    self.client.logger.error(f"Task {str(task)} has raised an exception during it's attempted task.stop(), unable to close app: {exception_stacktrace}")

        # Execution for this task has finished, return

    def append(self, task):
        """The append method is used to introduce a *task* object to
        the end of the list. This will cause the task to run once all the other activity's tasks
        have finished.
        """
        self.schedule.append(task)

    def prepend(self, task):
        """The prepend method is used to introduce a *task* object to the start of the list.
        This will cause the task to run once the current task has finished running.
        """
        self.schedule.prepend(task)

    async def run(self):
        """TODO
        """
        # While there are tasks in schedule to run
        while self.schedule:
            current_task = self.schedule.pop(0)

            # Run the task
            await self.run_task(current_task)

        # Schedule has finished

    def schedule_activity(self, activity_config, remaining_time):
        """Initialises a set of tasks for an activity and adds them to the scheduler.

        This function returns the total number of seconds that this activity has been
        allocated to run for.
        """
        # TODO: I'm fairly sure this function can be simplified

        # Minimum and maximum execution of activities are defined in minutes
        # Therefore, we need to multiply by 60 as the client's timers use
        # minutes.
        max_execution_time = activity_config["scheduling"]["maximum_execution"] * 60
        min_execution_time = activity_config["scheduling"]["minimum_execution"] * 60
        
        # Load the list of tasks we're going to schedule
        activity_tasks = []

        percentage_sum = 100

        for index, group in enumerate(activity_config["tasks"]):
            # If group["percentage_time_allocated"] == -1, we need to randomise the percentage of each group
            # Therefore, this will ensure that each task is randomised and that our percentages total to 100%
            # NOTE: I don't think this is mathematically fair and the first groups are more likely to take more
            # time.
            if group["percentage_time_allocated"] < 0:
                # If it's the last group, just use the rest of the percentage
                if index == len(activity_config["tasks"])-1:
                    time_percentage = percentage_sum
                else:
                    # Otherwise, pick a random percentage between the percentage sum we have left and zero.
                    time_percentage = randrange(0, percentage_sum)
                percentage_sum -= time_percentage
            else:
                # Otherwise, just use whatever value is passed
                time_percentage = group["percentage_time_allocated"]
    
            task_choices = []
            for task in group["task_choices"]:
                task_choices.append((task["selection_chance"], task))

            activity_tasks.append({"time": time_percentage, "tasks": task_choices})

        # Select a time between min and max time. This is how long the activity will run for.
        # If the remaining time left on this time block is less than the minimum time of the activity, run it for
        # the minimum time.
        if remaining_time < min_execution_time:
            selected_time = min_execution_time
        # If the remaining time is less than the maximum time, pick a random time between the minimum time and the remaining time
        # Both parameters are floored as randrange only accepts integers
        elif remaining_time < max_execution_time:
            selected_time = randrange(math.floor(min_execution_time), math.floor(remaining_time))
        # Otherwise, just pick a random time between minimum and maximum execution time for the activity
        else:
            selected_time = randrange(math.floor(min_execution_time), math.floor(max_execution_time))
        
        print(f"Total time allocated for this activity: {selected_time} seconds.")

        # Select a group of tasks within this activity and scale the amount of time they're allocated
        # based on the % of time allocated for the tasks
        for group in activity_tasks:
            # group["time"] is the amount of time this task has been allocated, in relation to the whole activity
            time = selected_time * group["time"] / 100
            # For each task in an activity, there are multiple choices. here, we pick a random one from this group
            selected = select_random(group["tasks"])
            # We then get the task 
            task = self.client.modules.get_task(selected["_id"]["module"], selected["_id"]["class"])

            # Sanity check that the task we get isn't None
            if task is None:
                self.client.logger.error("Attempted to retrieve task {}.{} however got None. Is the task's module inside config/general.json?".format(*selected["_id"].values()))

                # While this error could be handled, I think it's important we stop execution and let the user update the config.
                raise Exception("Attempted to retrieve task {}.{} however got None. Is the task's module inside config/general.json?".format(*selected["_id"].values()))

            print(f"Allocating task {str(task)} {time} seconds to run.")
            # And allocate it to the schedule
            self.append(
                task(self.client, activity_name=activity_config["name"], time=time, **selected["options"])
            )

        # Return the number of seconds this activity is set to run for
        return selected_time
