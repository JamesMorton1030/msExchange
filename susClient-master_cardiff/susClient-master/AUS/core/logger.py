
from platform import release, system, version
from socket import gethostbyname
import datetime
import os
from collections import defaultdict
import traceback

class SUSLogger:

    def __init__(self, client, name, log_type="activity", activity=None, module=None, task=None):
        self.client = client
        self.connection = client.connection
        self.name = name
        self.log_type = log_type

        if log_type not in self.client.config["logging"]:
            raise KeyError(log_type + " was not found in the logging config, please check log_type exists.")

        self.log_config = self.client.config["logging"][log_type]

        # As these values remain the same, we'll set them here
        self.global_header = {
            "source_ip": gethostbyname(self.client.hostname),
            "sim_type": "AUS",
            "hostname": self.client.hostname,
            "platform": system(),
            "release": release(),
            "version": version(),
            "username": self.client.username,
            self.log_type + "-log": {
                "additional": {
                    "logger": self.name
                }
            }
        }
        
        if activity:
            self.global_header[self.log_type + "-log"]["activity"] = activity
        if module:
            self.global_header[self.log_type + "-log"]["module"] = module
        if task:
            self.global_header[self.log_type + "-log"]["task"] = task

        # Ensure log directory exists
        if self.log_config["log_to_file"]["enabled"]:
            os.makedirs(os.path.dirname(self.log_config["log_to_file"]["file_path"]), exist_ok=True)

    def _log(self, level, message, **additional):
        """This method should not be called directly, use debug(), info(), warning(), error() or critical() instead."""
        log_data = self.global_header.copy()
        log_data["client_time"] = datetime.datetime.now(tz=datetime.timezone.utc).timestamp()

        if self.log_type == "activity" and "state" not in additional:
            print("WARNING: Activity logs should have 'state' attached. Please ensure you are providing the state= keyword argument to the {}() call. Using state 'UNKNOWN'.".format(level))
            traceback.print_stack()
            additional["state"] = "UNKNOWN"

        # Attach state, activity, module or task only if they exist
        if "state" in additional:
            log_data[self.log_type + "-log"]["state"] = additional.pop("state")


        log_data[self.log_type + "-log"]["log_type"] = level

        # Finally, push the rest of additional to the "additional" key
        log_data[self.log_type + "-log"]["additional"].update(additional)

        # We'll format the message with the kwargs arguments from additional, replacing with ??? if not found
        format_args = defaultdict(lambda: "???")
        format_args.update(additional)

        log_data[self.log_type + "-log"]["additional"]["message"] = message.format_map(format_args)

        if self.log_config["log_to_server"]["enabled"]:
            endpoint = self.log_config["log_to_server"]["endpoint"]
            self.connection.post(
                endpoint, json=log_data
            )

        if self.log_config["log_to_stdout"]["enabled"]:
            print("<{asc_time}> [{mode} - {level}] {name}: {message}".format(asc_time=datetime.datetime.now().strftime("%d/%m/%y %H:%M:%S"), level=level, mode=self.log_type, name=self.name, message=log_data[self.log_type + "-log"]["additional"]["message"]))

        if self.log_config["log_to_file"]["enabled"]:
            try:
                with open(self.log_config["log_to_file"]["file_path"], "a") as log_file:
                    print(log_data, file=log_file)
            except Exception as e:
                print("Failed to write log message to file", e)

    def debug(self, message, **additional):
        """Logs a debug message. If activity, module, task or state are passed as keyword arguments, these will be attached in the 'activity-log'/'debug-log' dictionaries, rather than 'additional'.

        Args:
            message (str): Log message.
            **additional (kwargs): Any additional data to be stored with the log.
        """
        self._log("DEBUG", message, **additional)

    def info(self, message, **additional):
        """Logs a info message. If activity, module, task or state are passed as keyword arguments, these will be attached in the 'activity-log'/'debug-log' dictionaries, rather than 'additional'.

        Args:
            message (str): Log message.
            **additional (kwargs): Any additional data to be stored with the log.
        """
        self._log("INFO", message, **additional)

    def warning(self, message, **additional):
        """Logs a warning message. If activity, module, task or state are passed as keyword arguments, these will be attached in the 'activity-log'/'debug-log' dictionaries, rather than 'additional'.

        Args:
            message (str): Log message.
            **additional (kwargs): Any additional data to be stored with the log.
        """
        self._log("WARNING", message, **additional)

    def error(self, message, **additional):
        """Logs a error message. If activity, module, task or state are passed as keyword arguments, these will be attached in the 'activity-log'/'debug-log' dictionaries, rather than 'additional'.

        Args:
            message (str): Log message.
            **additional (kwargs): Any additional data to be stored with the log.
        """
        self._log("ERROR", message, **additional)

    def critical(self, message, **additional):
        """Logs a critical message. If activity, module, task or state are passed as keyword arguments, these will be attached in the 'activity-log'/'debug-log' dictionaries, rather than 'additional'.

        Args:
            message (str): Log message.
            **additional (kwargs): Any additional data to be stored with the log.
        """
        self._log("CRITICAL", message, **additional)
