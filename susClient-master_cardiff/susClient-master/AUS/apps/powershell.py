from apps import BaseApp, BaseTask
import os
import subprocess
import random
import time
from threading import Timer

class RunScript(BaseTask):

    # TODO: Load from folder?
    def task_load(self, file_path="", script_content="", script_directory="", disable_timeout=False):
        # Techincally not needed, but we'll include it anyways to avoid errors with when the task ends
        self.app = self.client.modules.get_app("apps.powershell", "Powershell")(self.client)

        self.file_path = None
        self.disable_timeout = disable_timeout
        self.script_directory = script_directory

        if file_path and script_content:
            self.debug_logger.warning("Both file_path and script_content was given, ignoring script_content", file_path=file_path, script_content=script_content)

        if file_path:
            if not os.path.exists(file_path):
                self.activity_logger.warning("File {file_path} does not exist, using random script from {script_directory} instead", state="RUNNING", file_path=file_path, script_directory=script_directory)
            else:
                self.file_path = file_path
        elif script_content:
            # Write the script to a temporary file
            self.file_path = os.path.join(os.path.expandvars("%HOMEPATH%"), "Documents", "TemporaryScript.ps1")
            self.activity_logger.info("Writing script content to {file_path}", state="RUNNING", file_path=self.file_path, script_content=script_content)

            with open(self.file_path, "w") as script_file:
                script_file.write(script_content)
        
        # Either no file_path+script_content was passed, or the file_path that was provided was invalid 
        if self.file_path is not None:
            return

        if not os.path.isdir(script_directory):
            self.activity_logger.warning("Cannot get random script as {script_directory} does not exist", state="RUNNING", script_directory=script_directory)
            return
        
        # Check for the documents directory
        files = []

        for file in os.listdir(self.script_directory):
            file_path = os.path.join(self.script_directory, file)
            # Check whether this is a file or directory
            if os.path.isfile(file_path):
                # Basic file extension check
                if file_path.endswith(".ps1"):
                    # Add it to a list of files
                    files.append(file_path)

        if not len(files):
            self.activity_logger.warning("Could not find a viable random script in {script_directory}", state="RUNNING", script_directory=script_directory)
        else:
            self.file_path = os.path.abspath(random.choice(files))

    def start(self):
        super().start()

    def stop(self):
        super().stop()

    async def main(self):

        if not self.file_path:
            self.activity_logger.warning("No script was found to run, exiting early", state="RUNNING", file_path=self.file_path)
            return

        def process_timeout(process):
            self.activity_logger.warning("Script has run longer than allocated time", state="RUNNING")
            timer.cancel()
            process.kill()

        process = subprocess.Popen(["powershell.exe", "-ExecutionPolicy", "Bypass", self.file_path], shell=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        
        timer = None
        if not self.disable_timeout:
            timer = Timer(self.timer.total_time, process_timeout, args=[process])
            timer.start()

        # Poll process.stdout to show stdout live
        while True:
            try:
                output = process.stdout.readline()

                if output:
                    self.debug_logger.info("Received output from running {file_path}", file_path=self.file_path, output=output.decode().strip("\r\n"))

                if process.poll() is not None:
                    break
            except KeyboardInterrupt:
                self.debug_logger.info("Received KeyboardInterrupt, did someone manually stop SUS?")
                if timer:
                    timer.cancel()
                process.kill()
                time.sleep(5)
                break

        rc = process.poll()
        self.debug_logger.info("Received return code {return_code} from running {file_path}", file_path=self.file_path, return_code=rc)

# Because we initialise powershell within the runscript command, we don't actually need this class
class Powershell(BaseApp):
    """Wrapper around powershell.exe"""

    def open(self):
        return 

    def close(self):
        return

APPS = ["Powershell"]
TASKS = ["RunScript"]
