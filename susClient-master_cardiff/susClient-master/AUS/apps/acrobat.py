"""Notepad
"""

import time
import random
import os

from pywinauto import Desktop
from pywinauto.application import Application
from pywinauto.findbestmatch import MatchError
from pywinauto.findwindows import ElementNotFoundError
from pywinauto.base_wrapper import ElementNotVisible
from pywinauto import keyboard, mouse

from comtypes import COMError
from subprocess import Popen

from apps import BaseApp, BaseTask
from utils.pywinauto_text import type_keys_into_window
from utils.text_generator import TextGenerator
from utils.find_executable import get_executable_path

class ReadContent(BaseTask):
    """Opens a file and scrolls through it randomly.
    """

    def task_load(self, file_path="", add_file_path_to_command_line=False):
        # TODO: Add support for passing a PDF file path by command line argument like Word
        self.app = self.client.modules.get_app("apps.acrobat", APPS[0])(self.client)
        self.file_path = file_path
        self.add_file_path_to_command_line = add_file_path_to_command_line

    def start(self):
        """Starts Acrobat application"""
        # As per schema, call super().start() at the start of the task
        super().start()

        # Open the acrobat application
        if self.add_file_path_to_command_line:
            self.acrobat_app = self.app.open(command_line_file=self.file_path)
        else:
            self.acrobat_app = self.app.open()

    def stop(self):
        """Saves our file and calls BaseTask stop."""
        # As per schema, call super().stop() at the end of the task
        super().stop()

    async def main(self):
        # Check whether the file has been opened from the command line
        if self.app.command_line_file_opened:
            file_path = self.file_path
        else:
            # Firstly open the file
            # If no file path is passed, it will attempt to find a random file to open
            file_path = self.app.open_file(self.file_path)

        if file_path is None:
            self.activity_logger.warning("Attempted to open {file_path} but something went wrong", state="RUNNING", file_path=self.file_path)
        else:
            # Update file_path
            self.file_path = file_path

            if self.app.command_line_file_opened:
                self.activity_logger.info("Opened file {file_path} from the command line arguments to read through", state="RUNNING", file_path=self.file_path)
            else:
                self.activity_logger.info("Opened file {file_path} to read through", state="RUNNING", file_path=self.file_path)
                
            # While the timer is running
            while not self.timer:
                # Randomly scroll
                self.acrobat_app.top_window().wheel_mouse_input(wheel_dist=random.randint(-3, 3))
                time.sleep(random.uniform(0.5, 5))

class Acrobat(BaseApp):
    """Simple PDF viewing with the Adobe Acrobat application"""

    DEFAULT_DIRECTORY = "%USERPROFILE%\\Documents\\"

    def open(self, command_line_file=""):
        """Start the acrobat application"""

        self.command_line_file_opened = False

        # Check whether the application is already open
        if self.client.app_manager.is_open(self.__class__.__name__):
            self.app = self.client.app_manager.get(self.__class__.__name__)
            self.acrobat = self.app.top_window()
        else:
            # Otherwise, create the application.
            self.app = Application(backend="uia")
            self.app.start(get_executable_path("Acrobat Reader"))

            time.sleep(8)

            # See this issue: https://github.com/pywinauto/pywinauto/issues/553
            # As the adobe windows spawn somewhere else under this process, we have to reconnect to the application
            self.app.connect(title="Adobe Acrobat Reader DC")

            time.sleep(3)

            # If a command_line_file is specified, we need to check for a prompt
            # that tells us that this file couldn't be opened
            if command_line_file:
                # Assume that it's opened the file on the command line
                self.command_line_file_opened = True

                file_dialog = self.app.top_window().window(title="Adobe Acrobat")
                if file_dialog.exists():
                    dialog_text = file_dialog.child_window(title="There was an error opening this document. This file cannot be found.", control_type="Text")
                    if dialog_text.exists():
                        # If this prompt comes up and we've found the error prompt's text, set it to false
                        self.command_line_file_opened = False

                    # Make sure we click the OK button
                    file_dialog.window(title="OK").click()

            # Check for the prompt that asks if we'd like to set reader to our default pdf application
            self.acrobat = self.app.top_window()
            
            try:
                # Wait for this prompt to appear, doesn't always happen quickly..
                time.sleep(8)

                self.acrobat.child_window(title="Acrobat Reader").child_window(title="No", control_type="Button").click()
            except ElementNotFoundError:
                # No prompt, guess we can carry on!
                pass
            
            # Add to app manager
            self.client.app_manager.add(self.__class__.__name__, self.app)

        return self.app

    def close(self):
        try:
            # Attempt to close the app nicely
            self.app.kill(soft=True)
        except (ElementNotVisible, COMError):
            # If there's a element not visible error, this means that usually the window has
            # already closed due to another app.
            # Attempt an aggressive close
            # Check whether the process is running
            if self.app.is_process_running():
                # If it's still running, force close
                self.app.kill(soft=False)

        # Remove the application from app_manager
        self.client.app_manager.remove(self.__class__.__name__)

    def open_file(self, file_path):
        """A method to open a file in Acrobat.
        Returns the file path that was opened.
        """
        # Firstly enter CTRL + O
        self.acrobat.type_keys("^o")

        # If no filepath is passed, let's open a random PDF if we can find one
        if not file_path:
            documents_directory = os.path.abspath(os.path.expandvars(self.DEFAULT_DIRECTORY))

            files = []

            # Check for the documents directory
            for file in os.listdir(documents_directory):
                file_path = os.path.join(documents_directory, file)
                # Check whether this is a file or directory
                if os.path.isfile(file_path):
                    # Basic file extension check
                    if file_path.endswith(".pdf"):
                        # Add it to a list of files
                        files.append(file_path)
            
            if len(files):
                file_path = random.choice(files)
            else:
                # No file could be found
                return None

        self.debug_logger.info("Attempting to access open dialog for {file_path}", file_path=file_path)

        # Wait before typing file name
        time.sleep(3)

        # Get the open dialog
        open_dialog = self.acrobat.window(title="Open", control_type="Window").wait("exists")
        
        # Write the file path
        type_keys_into_window(open_dialog.descendants(class_name="Edit")[0], file_path)

        # Wait before clicking open
        time.sleep(1)

        # Luckily for us, the open button has a auto ID of 1
        self.acrobat.child_window(auto_id="1", control_type="Button").click()

        time.sleep(3)

        try:
            open_dialog_children = open_dialog.children(title="Open", control_type="Window")
        except ElementNotFoundError:
            # Open dialog has disappeared, assume we've opened it
            return file_path
        
        if len(open_dialog_children):
            time.sleep(2)

            file_doesnt_exist_dialog = open_dialog_children[0]

            # If the file doesn't exist, a dialog pops up with an OK button
            # If this dialog pops up, we can set attempt_open false
            file_doesnt_exist_dialog.children(title="OK")[0].click()

            # Close the open dialog and set file_exists to false, so we can create the file
            open_dialog.close()
            
            # Return none as no file was opened
            return None

        # Return the file path that we opened
        return file_path

APPS = ["Acrobat"]
TASKS = ["ReadContent"]
