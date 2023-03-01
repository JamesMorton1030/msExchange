from apps import BaseApp, BaseTask
import os
import subprocess
import random
import time
import shlex
from threading import Timer

class RunProcess(BaseTask):

    def task_load(self, process="", arguments="", requires_file=False, file_path="", random_file_extension="", random_file_directory="", disable_timeout=False):
        # Techincally not needed, but we'll include it anyways to avoid errors with when the task ends
        self.app = self.client.modules.get_app("apps.process", "Process")(self.client)
        self.process = process
        self.arguments = arguments
        self.requires_file = requires_file

        if not requires_file: 
            return

        self.file_path = None
        self.disable_timeout = disable_timeout

        if not file_path and not random_file_directory:
            self.activity_logger.error("No file path or random file directory was given")
            return

        if file_path:
            if not os.path.exists(file_path):
                if random_file_directory:
                    self.activity_logger.warning("File {file_path} does not exist, trying to find random file from {random_file_directory} instead", state="RUNNING", file_path=file_path, random_file_directory=random_file_directory)
                else:
                    self.activity_logger.warning("File {file_path} does not exist and no random_file_directory was passed")
                    return
            else:
                self.file_path = file_path
                return
    
        if not os.path.isdir(random_file_directory):
            self.activity_logger.warning("Cannot get random file as {random_file_directory} does not exist", state="RUNNING", random_file_directory=random_file_directory)
            return
        
        # Check for the documents directory
        files = []

        print(random_file_extension)

        for file in os.listdir(random_file_directory):
            file_path = os.path.join(random_file_directory, file)
            # Only check the file extension if one is passed
            if random_file_extension and not file_path.endswith("." + random_file_extension):
                continue
        
                # Add it to a list of files
            files.append(file_path)

        if not len(files):
            self.activity_logger.warning("Could not find a viable random file in {random_file_directory}", state="RUNNING", random_file_directory=random_file_directory)
        else:
            self.file_path = os.path.abspath(random.choice(files))
            self.activity_logger.info("Found random file {file_path} for process arguments", state="RUNNING", file_path=self.file_path)

    def start(self):
        super().start()

    def stop(self):
        super().stop()

    async def main(self):
        
        # Split arguments and replace with file_path
        arguments = [arg if arg != "{file_path}" else self.file_path for arg in shlex.split(self.arguments)]

        if self.requires_file and not self.file_path:
            self.activity_logger.warning("No file_path was found to run, exiting early", state="RUNNING", file_path=self.file_path)
            return

        def process_timeout(process):
            self.activity_logger.warning("Script has run longer than allocated time", state="RUNNING")
            timer.cancel()
            process.kill()

        subprocess_args = [self.process]
        subprocess_args.extend(arguments)

        process = subprocess.Popen(subprocess_args, shell=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        
        timer = None
        if not self.disable_timeout:
            timer = Timer(self.timer.total_time, process_timeout, args=[process])
            timer.start()

        # Poll process.stdout to show stdout live
        while True:
            try:
                output = process.stdout.readline()

                if output:
                    self.debug_logger.info("Received output from running {process}", process=self.process, arguments=arguments, output=output.decode().strip("\r\n"))

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
        self.debug_logger.info("Received return code {return_code} from running {process}", state="RUNNING", process=self.process, return_code=rc)

# Because we initialise process within the RunProcess command, we don't actually need this class
class Process(BaseApp):
    """Wrapper around Runprocess Task"""

    def open(self):
        return 

    def close(self):
        return

APPS = ["Process"]
TASKS = ["RunProcess"]
