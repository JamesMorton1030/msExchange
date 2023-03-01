from logger import SUSLogger
import pywintypes
import ctypes
import win32
import win32pipe
import win32file
import json
import time
import requests
import socket
import subprocess
import os
import traceback

from SMWinservice import SMWinservice
import StartElevatedProcess

# different system states
LOGGED_OUT = 0
WAITING_TO_LOGIN = 1
LOGGED_IN = 2
WAITING_TO_UNLOCK = 3

HOTDESKING_DIRECTORY = os.path.dirname(os.path.abspath(__file__))

PROCESS_TO_IMPERSONATE = "winlogon"
LOGIN_VBS_SCRIPT = os.path.join(HOTDESKING_DIRECTORY, "utilities", "login.vbs")
LOGIN_CMD_SCRIPT = os.path.join(HOTDESKING_DIRECTORY, "utilities", "login.cmd")
UNLOCK_VBS_SCRIPT = os.path.join(HOTDESKING_DIRECTORY, "utilities", "unlock.vbs")
UNLOCK_CMD_SCRIPT = os.path.join(HOTDESKING_DIRECTORY, "utilities", "unlock.cmd")
CSCRIPT = "C:\Windows\system32\cscript.exe"

# Note that this expects the username and password to be appended to the end
# Also, we prefer the token method of getting highest privileges, rather than using psexec, therefore this has not been tested
PSEXEC_ARGS = [
    os.path.join(HOTDESKING_DIRECTORY, "utilities", "PsExec64.exe"),
    "-d",
    "-x",
    "-s",
    "-w",
    "C:/Program Files/SUS/Hotdesking/",
    CSCRIPT,
    LOGIN_VBS_SCRIPT,
]

HOTDESKING_ENDPOINT = "/api/hotdesk"


class AutoLogon(SMWinservice):
    _svc_name_ = "SUSHotdesking"
    _svc_display_name_ = "SUS Hotdesking"
    _svc_description_ = "SUS Toolkit: Hotdesking Service"

    # function is called when the service is told to start
    def start(self):

        try:
            self.is_running = True
            self.system_state = LOGGED_OUT

            # load config file and decode json data
            with open(
                os.path.join(HOTDESKING_DIRECTORY, "config.json"), "r"
            ) as config_file:
                self.config = json.load(config_file)

            self.config["api_url"] = self.config["api_url"].rstrip("/")

            # create loggers
            self.debug_logger = SUSLogger(self.config, "hotdesking", log_type="debug")
            self.debug_logger.info("Debug Logger Created")

            self.activity_logger = SUSLogger(self.config, "hotdesking", log_type="activity")

        except Exception as e:
            print(repr(e))
            exit(-1)

    # called when the service is told to stop - it won't stop straight away
    def stop(self):
        self.is_running = False

    def get_credentials(self):
        request_url = self.config["api_url"] + "/api/hotdesk/" + socket.gethostname()

        retry_count = 10
        # sit in loop until credentials obtained, POST returns error or retries exceeded
        while retry_count > 0:
            try:
                self.debug_logger.info(
                    "Sending POST request to {0}".format(request_url),
                )

                # Pass profile tags to server as json
                r = requests.post(request_url, timeout=5)

                if r is None:
                    self.debug_logger.warning("Request failed (endpoint returned None)")
                    self.debug_logger.info("Retrying. {0} attempts remaining.".format(retry_count))
                # handle return status codes according to schema
                if r.status_code == 200:
                    credentials = r.json()
                    self.debug_logger.info(
                        "Received username: {username}, password: {password}, delay: {delay}",
                            username=credentials["username"],
                            password=credentials["password"],
                            delay=credentials["delay"],
                        
                    )
                    return credentials
                elif r.status_code == 204:
                    self.debug_logger.info("Credentials withheld (endpoint returned 204), retrying")
                    time.sleep(10)
                    # allow infinite retries if credentials withheld
                    retry_count = 10
                elif r.status_code == 503:
                    self.debug_logger.warning("Hotdesking not enabled on server (endpoint returned 503)")
                    self.debug_logger.info("Exiting hotdesking service")
                    self.stop()
                elif r.status_code == 405:
                    self.debug_logger.warning("Hotdesking sent invalid request (endpoint returned 405)")
                    self.debug_logger.info(
                        "Retrying. {} attempts remaining.".format(retry_count),
                    )
                else:
                    self.debug_logger.warning("Request failed (endpoint returned {})".format(r.status_code))
                    self.debug_logger.info("Retrying. {0} attempts remaining.".format(retry_count))

            except (requests.exceptions.RequestException, ConnectionResetError) as e:
                self.debug_logger.warning("Exception occured during request", exception=traceback.format_exc())
                self.debug_logger.info("Retrying. {0} attempts remaining.".format(retry_count))

            retry_count -= 1

        self.debug_logger.warning(
            "Retry count exceeded, could not retrieve credentials from server",
        )

        return None

    def main(self):
        try:
            self.run()
        except Exception as e:
            self.debug_logger.critical("Got exception while running", exception=traceback.format_exc())
            exit(-1)

    def run(self):
        # comfort sleep
        time.sleep(10)

        timer = 0
        username = ""
        password = ""

        while self.is_running:

            # sleep for 1 second and decrement timer
            time.sleep(1)
            timer -= 1
            
            # make sure the timer doesn't go negative
            if timer < 0:
                timer = 0

            if self.system_state == LOGGED_OUT:
                self.debug_logger.info("Connecting to server")

                credentials = self.get_credentials()

                if credentials is not None:
                    username = credentials["username"]
                    password = credentials["password"]
                    timer = credentials["delay"]
                else:
                    if self.config["default_credentials"]["enabled"]:
                        timer = self.config["default_credentials"]["delay"]
                        username = self.config["default_credentials"]["username"]
                        password = self.config["default_credentials"]["password"]
                    else:
                        self.debug_logger.info("Failed to retrieve credentials from server and default credentials are disabled, exiting")
                        self.stop()
                    
                self.system_state = WAITING_TO_LOGIN

            elif self.system_state == WAITING_TO_LOGIN:
                # check if we need to log in now, if so then login
                if timer != 0:
                    continue

                try:
                    if self.config["use_psexec"]:
                        self.do_login_psexec(username, password)
                    else:
                        self.do_login(username, password)
                except Exception as e:
                    self.debug_logger.error("Failed to login", exception=traceback.format_exc())

                    self.activity_logger.error("Failed to login due to exception when attempting login process.", state="HOTDESKING")
                    self.is_running = False

            elif self.system_state == LOGGED_IN:
                # check for state change and handle accordingly
                change_received = False
                while not change_received:
                    try:
                        # open sus pipe and retrieve message
                        handle = win32file.CreateFile(
                            r"\\.\\pipe\\SUSHotdesking",
                            win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                            0,
                            None,
                            win32file.OPEN_EXISTING,
                            0,
                            None,
                        )

                        message = win32pipe.SetNamedPipeHandleState(
                            handle, win32pipe.PIPE_READMODE_MESSAGE, None, None
                        )

                        if message == 0:
                            self.debug_logger.error("Pipe returned: {0}".format(message))
                        # parse message and change state
                        while True:
                            state = win32file.ReadFile(handle, 64 * 1024)
                            self.debug_logger.info(
                                "Recieved pipe message: {0}".format(state),
                            )

                            state_parsed = state[1].decode().split(" ")
                            timer = int(state_parsed[1])

                            if state_parsed[0] == "LOCK":
                                self.debug_logger.info("Change State: LOCK")
                                self.system_state = WAITING_TO_UNLOCK
                                change_received = True
                            elif state_parsed[0] == "LOGOFF":
                                self.debug_logger.info("Change State: LOGOFF")
                                self.system_state = LOGGED_OUT
                                change_received = True
                            else:
                                self.debug_logger.error("Unknown state received")

                    except pywintypes.error as e:
                        if e.args[0] == 2:
                            # don't log as this clutters up the debug log
                            # expected behaviour while client starts
                            time.sleep(1)
                        elif e.args[0] == 109:
                            self.debug_logger.info("SUS Client Pipe Broken")
                            change_received = True

            elif self.system_state == WAITING_TO_UNLOCK:
                # check if we need to unlock now, if so then unlock
                if timer == 0:
                    try:
                        self.do_unlock(password)
                    except Exception as e:
                        self.debug_logger.error("Failed to unlock", exception=traceback.format_exc())
                        self.activity_logger.error("Failed to unlock due to exception when attempting login process.", state="RUNNING")

                        self.is_running = False
                    pass

            else:
                self.debug_logger.error("Unknown state: {system_state}", system_state=self.system_state)
                exit(-1)

    def do_login_psexec(self, username, password):

        # Log to both the debug log and the activity log
        self.debug_logger.info("Starting login via PSExec with {username}, {password}", username=username, password=password)

        self.activity_logger.info("Logging in with {username}, {password}", state="START", username=username, password=password)

        subprocess.run(PSEXEC_ARGS + [username, password])

        self.system_state = LOGGED_IN

    def do_login(self, username, password):

        # Log to both the debug log and the activity log
        self.debug_logger.info("Starting login via token elevation with {username}, {password}", username=username, password=password)

        self.activity_logger.info("Logging in with {username}, {password}", state="START", username=username, password=password)

        # grab pid of winlogon
        pid = StartElevatedProcess.find_process_id(PROCESS_TO_IMPERSONATE)

        self.debug_logger.info("Got process ID of {process}: {pid}", process=PROCESS_TO_IMPERSONATE, pid=pid)

        # grab handle of winlogon
        handle = StartElevatedProcess.get_process_handle(pid)

        self.debug_logger.info("Got handle of {process}", process=PROCESS_TO_IMPERSONATE)

        # get the token of winlogon
        token = StartElevatedProcess.get_process_token(handle)

        self.debug_logger.info("Got token of {process}", process=PROCESS_TO_IMPERSONATE)

        # create a new token to use for cmd
        new_token = StartElevatedProcess.duplicate_and_escalate_token(token)

        self.debug_logger.info("Duplicated {process} token and esculated it", process=PROCESS_TO_IMPERSONATE)

        login_program = r"C:\Windows\System32\cmd.exe"
        login_args = r"""/C "{}" {} {}""".format(LOGIN_CMD_SCRIPT, username, password)

        self.debug_logger.info(
            "Calling \"{} {}\" to login".format(login_program, login_args),
        )

        # run cmd with new token and args
        StartElevatedProcess.create_new_process(
            new_token, login_program, login_args, os.path.join(HOTDESKING_DIRECTORY, "utilities")
        )

        self.debug_logger.info("Privileged login script has been started")
        self.activity_logger.info("Privileged login script has been started, login should commence soon", state="END")

        self.system_state = LOGGED_IN

    def do_unlock(self, password):

        self.debug_logger.info("Starting unlock procedure with {password}", password=password)
        self.activity_logger.info("Starting unlock procedure with {password}", state="START")


        # grab pid of winlogon
        pid = StartElevatedProcess.find_process_id(PROCESS_TO_IMPERSONATE)

        self.debug_logger.info("Got process ID of {process}: {pid}", process=PROCESS_TO_IMPERSONATE, pid=pid)

        # grab handle of winlogon
        handle = StartElevatedProcess.get_process_handle(pid)

        self.debug_logger.info("Got handle of {process}", process=PROCESS_TO_IMPERSONATE)

        # get handle of winlogon
        token = StartElevatedProcess.get_process_token(handle)

        self.debug_logger.info("Got token of {process}", process=PROCESS_TO_IMPERSONATE)

        # create new token to use for cmd
        new_token = StartElevatedProcess.duplicate_and_escalate_token(token)

        self.debug_logger.info("Duplicated {process} token and esculated it", process=PROCESS_TO_IMPERSONATE)

        self.debug_logger.info(
            "Calling {} {} {} to unlock".format(CSCRIPT, LOGIN_VBS_SCRIPT, password),
        )

        unlock_program = r"C:\Windows\System32\cmd.exe"
        unlock_args = r"""/C "{}" {}""".format(LOGIN_CMD_SCRIPT, password)

        # start cmd with token and args
        StartElevatedProcess.create_new_process(
            new_token, unlock_program, unlock_args, os.path.join(HOTDESKING_DIRECTORY, "utilities")
        )

        self.debug_logger.info("Privileged unlock script has been started")
        self.activity_logger.info("Privileged unlock script has been started, login should commence soon", state="END")

        self.system_state = LOGGED_IN


if __name__ == "__main__":
    AutoLogon.parse_command_line()
