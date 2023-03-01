"""The client module contains the client which connects all the parts
of the simulator together.
"""

from calendar import day_name
from datetime import datetime
from getpass import getuser
from socket import gethostname
from time import time, sleep

from core.connection import Connection
from core.appmanager import ApplicationManager
from core.modules import ModuleManager
from core.scheduler import Scheduler
from core.logger import SUSLogger

from utils import select_random, str_to_time

import ctypes
import subprocess
import os
import asyncio
import sys
import socket
import subprocess

try:
    import win32file, win32pipe
except ModuleNotFoundError:
    # Linux does not have win32file/pipe
    pass

class Client:
    """The client object manages and connects everything else.
    """

    def __init__(self, config):
        self.hostname = gethostname()
        self.username = getuser()

        # Just a sanity check for the config API url
        self.config = config
        self.config["api_url"] = self.config["api_url"].rstrip("/")

        self.connection = Connection(self.config["api_url"])

        self.logger = SUSLogger(self, "client")
        self.debug_logger = SUSLogger(self, "client", log_type="debug")

        self.logger.info("Starting AUS", state="START")
        
        self.modules = ModuleManager(config["apps"])
        self.app_manager = ApplicationManager(self)
        self.scheduler = Scheduler(self)
        self.profile = None

        # The ready variable stores whether the client has successfully loaded everything that
        # it needs. Before client.start() is called, .ready should be checked that it is true.
        # Check whether a profile has been successfully loaded
        self.ready = self.fetch_profile()

        # Check whether development mode is enabled, if so, display a message
        if self.config["development_mode"]:
            self.debug_logger.info("Development mode is enabled - exceptions in tasks will be raised as usual")

    def fetch_profile(self):
        """Attempts to fetch the profile from the server returning *True* if successful or *False* if not.
        """
        # Get the profile based on username and hostname
        response = self.connection.get("/api/profiles/retrieve_profile/{hostname}/{username}".format(
                hostname=self.hostname, username=self.username
            )
        )

        # Non-200 means something went wrong.
        if response is None or response.status_code != 200:
            self.logger.error("Failed to retrieve profile, status code {status_code}", state="START", status_code=response.status_code if response is not None else "N/A")
            return False

        self.logger.info("Successfully retrieved profile from server", state="START")
        self.profile = response.json()
        return True

    def run(self):
        """This method starts the client, running each of the tasks
        specified by the currently selected activity. It will only stop
        when the client reaches the end of the current session in the
        timetable.
        """
        # Get the days schedule
        day = day_name[datetime.now().weekday()].lower()
        schedule = self.profile["schedules"][day]
        if not schedule:
            self.logger.warning("Client was started but had no schedule for that day.", state="START")
            return
        
        # Log that we're starting
        self.logger.info("Starting schedule execution now", state="START")

        # For each time block
        for block in schedule["time_blocks"]:
            # Load the end_times and activities
            end_time = str_to_time(block["timing"]["end"])
            activities = []
            for activity in block["activities"]:
                activities.append(
                    (activity["scheduling"].pop("selection_chance"), activity)
                )
            # While there is still time remaining run an activity
            remaining = end_time - time()
            while remaining > 0:
                activity = select_random(activities)
                # Append the tasks to the scheduler
                # TODO: This function weirdly returns the number of seconds the activity runs for. This is a weird implementation used
                # so we can log how long this activity has been allocated. Could we rework this in the future?
                total_time_allocated = self.scheduler.schedule_activity(activity, remaining)
                # Log the start of the activity
                self.logger.info("{} was scheduled".format(activity["name"]), state="START", activity=activity["name"], time_allocated="{} seconds".format(int(total_time_allocated)))
                # Actually run the tasks
                asyncio.run(self.scheduler.run())
                # Log the end of the activity
                self.logger.info("{} has finished".format(activity["name"]), state="END", activity=activity["name"])
                # Update the remaining amount of time
                remaining = end_time - time()

        # Once we've finished the schedule
        self.logger.info("Ending schedule execution now", state="END")

        if self.config["sysmon_logs"]["collect_logs"]:
            self.logger.info("Attempting to run sysmon log collection script", state="START")

            # We can now call the sysmon collection scritp
            working_directory = os.getcwd()

            # This function uses the microsoft tool psexec64 to run a process with elevated permissions, using local administrator creds
            # This calls the powershell script which will take sysmon logs and convert them to a .csv
            # This csv file can then be collected after this process exits and uploaded to the server
            sysmon_collection_process = subprocess.run(['sysmon/psexec64.exe', '-accepteula', '-u', self.config["sysmon_logs"]["local_administrator_username"], '-p', self.config["sysmon_logs"]["local_administrator_password"], 'powershell.exe', '-ExecutionPolicy', 'Unrestricted', '-File', self.config["sysmon_logs"]["powershell_script_path"]], cwd=working_directory)
            
            self.logger.info("Sysmon log collection script finished", state="END")

            # Our script contains the PREFERRED method of copying to a networked share, therefore this code below is not needed.

            # TODO: This code should be updated to use the file format in the script, if you wish to use the upload to SUS server rather than
            # copying to a networked share.
            if self.config["sysmon_logs"]["upload_to_server"]:
                self.logger.info("Attempting to upload sysmon logs", state="START")
                
                # Now check whether we can find the log file
                datetime_string = datetime.now().strftime("%d-%m-%Y")
                csv_file_path = self.config["sysmon_logs"]["upload_csv_file_path"].format(datetime_string)
                if os.path.exists(csv_file_path):
                    # We can locate the csv file, upload it to the server
                    # TODO: Check what parameters we should be sending instead of date/profile_id (maybe hostname?)
                    response = self.connection.post(self.config["sysmon_logs"]["upload_endpoint"], 
                        files={
                            "csv_file": open(csv_file_path, "rb")
                        },
                        data={
                            "profile_id": self.profile["_id"],
                            "log_date": datetime_string
                        }
                    )
                    if not response or response.status_code != 200:
                        self.logger.warning("Failed to upload sysmon logs, response code: {}".format(response.status_code if response else "N/A"), state="END")
                    else:
                        self.logger.info("Successfully uploaded sysmon logs", state="END")
                else:
                    self.logger.warning("No sysmon logs found in expected directory: {}.".format(csv_file_path), state="END")

        # self.lock() could also be used, but self.logout() must be used for hotdesking to work
        self.logout()

    def lock(self):
        """
        This function will lock the computer and communicate to hotdesking it has locked it
        """
        self.logger.info("Locking computer now", state="START")

        # create the pipe as "server"
        pipe = win32pipe.CreateNamedPipe(r'\\.\\pipe\\SUSHotdesking', win32pipe.PIPE_ACCESS_DUPLEX, 
            win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
            1, 65536, 65536, 0, None)

        try:
            self.debug_logger.info("Connecting to hotdesking pipe")
            win32pipe.ConnectNamedPipe(pipe, None)
            
            # format of message, delay is in seconds: LOCK <int>
            self.debug_logger.info("Sending locking signal to hotdesking pipe (delay = 1)")
            win32file.WriteFile(pipe, str.encode(f'LOCK 1'))
            sleep(1)
            self.debug_logger.info("Sent locking sginal to hotdesking pipe")

        finally:
            win32file.CloseHandle(pipe)
            self.logger.info("Closing pipe and locking machine", state="END")

            # This will lock your machine!
            ctypes.windll.user32.LockWorkStation() 
    
    def logout(self):
        """
        This function will log off the computer and communicate to hotdesking it has logged off
        """
        self.logger.info("Logging out now", state="START")

        # Check whether we are on Windows or Linux
        if sys.platform == "win32":
            pipe = win32pipe.CreateNamedPipe(r'\\.\\pipe\\SUSHotdesking', win32pipe.PIPE_ACCESS_DUPLEX, 
            win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
            1, 65536, 65536, 0, None)

            try:
                self.debug_logger.info("Connecting to hotdesking pipe")
                win32pipe.ConnectNamedPipe(pipe, None)
                
                self.debug_logger.info("Sending logoff signal to hotdesking pipe (delay = 10)")
                win32file.WriteFile(pipe, str.encode(f'LOGOFF 10'))
                
                self.debug_logger.info("Sent logoff sginal to hotdesking pipe")
            finally:
                win32file.CloseHandle(pipe)
                self.logger.info("Closing pipe and logging off machine", state="END")
                
                #this will logoff the machine!
                ctypes.windll.user32.ExitWindowsEx(0, 4)
        elif sys.platform == "linux":
            self.logger.info("Fetching credentials for next login", state="START")

            # If we're running on Linux, we need to execute the set_next_login_user.sh command with the new username + delay
            response = self.connection.request(
                "post", "/api/hotdesk/{}".format(socket.gethostname()), json=self.config["hotdesk_settings"]["profile_tags"]
            )

            if response.status_code == 200:
                # Run the script with the parameters received
                hotdesk_creds = response.json()

                self.logger.info("Received new credentials from server, setting next login user.", username=hotdesk_creds["username"], delay=hotdesk_creds["delay"], state="RUNNING")

                sleep(5)

                try:
                    command = subprocess.check_output(["sudo", "/usr/local/bin/set_next_login_user.sh", hotdesk_creds["username"], str(hotdesk_creds["delay"])])
                    self.logger.info("Successfully set credentials for next login.", username=hotdesk_creds["username"], delay=hotdesk_creds["delay"], state="END")
                except OSError:
                    self.logger.error("Attemped to run set login script but an error occured. Has SUS been installed correctly?", state="END")

                # Our script will now reboot the system
            else:
                self.logger.error("Attempted to retrieve credentials from hotdesking but got status code: {}".format(response.status_code), state="END")
