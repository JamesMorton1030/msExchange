import requests
import socket
import time
import json
import platform as system_platform
import enum
import os
import datetime


class LogType(enum.Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


def get_body():
    # Construct the data to post to server
    return {
        "source_ip": socket.gethostbyname(socket.gethostname()),
        "sim_type": "HD",
        "hostname": system_platform.node(),
        "platform": system_platform.system(),
        "release": system_platform.release(),
        "version": system_platform.version(),
        "username": "N/A",
        "client_time": datetime.datetime.now(tz=datetime.timezone.utc).timestamp(),
    }


class BaseLogger:
    def __init__(self, type, config):
        self.type = type
        self.config = config
        self.log_config = self.config["logging"][self.type]

        self.log_endpoint = self.log_config["log_to_server"]["endpoint"]
        self.log_file_path = self.log_config["log_to_file"]["file_path"]

        os.makedirs(
            os.path.dirname(self.log_file_path),
            exist_ok=True,
        )

    def log_to_file(self, json_data):
        try:
            with open(self.log_file_path, "a") as log_file:
                print(json_data, file=log_file)
        except Exception as e:
            print("Got error while attempting to write to log file")
            print(e)

    def log_to_server(self, json_data):
        try:
            # post the data to server
            requests.post(
                self.log_endpoint,
                json=json_data,
            )
        except (TimeoutError, requests.exceptions.RequestException) as e:
            # some sort of connection/http response issue
            print("Got error while attemping to send log to server")
            print(e)

    def _log(self, log_data):
        if self.log_config["log_to_server"]["enabled"]:
            self.log_to_server(log_data)

        if self.log_config["log_to_file"]["enabled"]:
            self.log_to_file(log_data)

        if self.log_config["log_to_stdout"]["enabled"]:
            print(log_data)


class ActivityLogger(BaseLogger):
    """The class which is responsible for commiting activity logs to server and to a local activity log file"""

    def __init__(self, config):
        super().__init__("activity", config)

    def log(self, log_type, activity, state, message, **additional):
        body = get_body()

        body["activity-log"] = {
            "log_type": log_type.value,
            "activity": activity,
            "state": state,
            "message": message,
            "additional": additional,
        }

        self._log(body)


class DebugLogger(BaseLogger):
    """The class which is responsible for committing debugging logs to server and to a local debug log file"""

    def __init__(self, config):
        super().__init__("debug", config)

    def log(self, log_type, message, **additional):
        body = get_body()

        body["activity-log"] = {
            "log_type": log_type.value,
            "message": message,
            "additional": additional,
        }

        self._log(body)
