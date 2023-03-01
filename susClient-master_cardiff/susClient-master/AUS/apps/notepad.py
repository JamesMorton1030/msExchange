"""Notepad
"""

import ctypes
import time
import random
import string
import os

from pywinauto.application import Application
from pywinauto.findbestmatch import MatchError
from pywinauto.findwindows import ElementNotFoundError
from pywinauto.base_wrapper import ElementNotVisible
from pywinauto import keyboard, mouse
from comtypes import COMError

from apps import BaseApp, BaseTask
from utils.pywinauto_text import type_keys_into_window
from utils.text_generator import TextGenerator

class ReadContent(BaseTask):
    """Opens a file and scrolls through it randomly.
    """

    def task_load(self, file_path="", add_file_path_to_command_line=False):
        self.app = self.client.modules.get_app("apps.notepad", APPS[0])(self.client)
        self.file_path = file_path
        self.add_file_path_to_command_line = add_file_path_to_command_line

        self.notepad_app = None

    def start(self):
        """Starts notepad application"""
        # As per schema, call super().start() at the start of the task
        super().start()

        # Open the notepad application
        if self.add_file_path_to_command_line:
            self.notepad_app = self.app.open(command_line_file=self.file_path)
        else:
            self.notepad_app = self.app.open()

    def stop(self):
        """Saves our file and calls BaseTask stop."""
        # Double check that the notepad process is still running
        # In the event it somehow got closed, we need to ensure that we fire close_app so that it's removed from AppManager
        if self.notepad_app is None or not self.notepad_app.is_process_running():
            self.close_app = True

        # As per schema, call super().stop() at the end of the task
        super().stop()

    async def main(self):
        # Check whether the file has been opened from the command line
        if self.app.command_line_file_opened:
            file_path = self.file_path
        else:
            # Firstly open the file
            # If no file path is passed (and because attempt_open = True) it will attempt to find a random file to open
            file_path = self.app.open_file(self.file_path, attempt_open=True)

        if file_path is None:
            self.activity_logger.warning("Attempted to open file {file_path} but something went wrong", state="RUNNING", file_path=self.file_path)
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
                self.notepad_app.top_window().wheel_mouse_input(wheel_dist=random.randint(-3, 3))
                time.sleep(random.uniform(0.5, 5))

class WriteContent(BaseTask):
    """Writes the string in content (writes lorem ipsum if content is '')
    to a notepad file at file_path (a random file if file_path=='')
    """

    def task_load(self, content="", file_path="", attempt_open=False, typing_delay=0.08, line_delay=0.1):
        self.app = self.client.modules.get_app("apps.notepad", APPS[0])(self.client)
        self.content = content
        self.text_generator = TextGenerator(self.client) #so we don't have to re-instantiate it each time
        self.file_path = file_path
        self.attempt_open = attempt_open
        self.typing_delay = typing_delay
        self.line_delay = line_delay

        self.notepad_app = None

    def start(self):
        """Starts notepad application"""
        # As per schema, call super().start() at the start of the task
        super().start()

        # Open the notepad application
        self.notepad_app = self.app.open()

    def stop(self):
        """Saves our file and calls BaseTask stop."""
        # Double check that the notepad process is still running
        # In the event it somehow got closed, we need to ensure that we fire close_app so that it's removed from AppManager
        if self.notepad_app is None or not self.notepad_app.is_process_running():
            self.close_app = True

        # As per schema, call super().stop() at the end of the task
        super().stop()

    def switch_in(self):
        """Gets focus on the window"""
        self.notepad_app.top_window().set_focus()
        
        super().switch_in()

    def switch_out(self):
        super().switch_out()

    async def main(self):
        # Firstly open the file
        # If we pass no file path, open_file will open a random file. Therefore, we can update
        # the file path in this task.
        file_path = self.app.open_file(self.file_path, self.attempt_open)

        if file_path is None:
            self.activity_logger.warning("Attempted to open file {file_path} but something went wrong", state="RUNNING", file_path=self.file_path)
        else:
            # Update our file path
            self.file_path = file_path

            self.activity_logger.info("Opened file {file_path} to write content into", state="RUNNING", file_path=self.file_path)
            
            # If we have a given content, write until it's done then exit
            if self.content:
                # Write content
                self.app.write_content(self.content, typing_delay=self.typing_delay, line_delay=self.line_delay)
            else:
                # Otherwise, write random sentences until timer has finished
                while not self.timer:
                    # Generate a list of paragraphs
                    paragraphs = [self.text_generator.gen_paragraph() for _ in range(random.randint(2, 6))]
                    for paragraph in paragraphs:
                        # Write paragraph into body
                        self.app.write_content(paragraph + "\n", typing_delay=self.typing_delay, line_delay=self.line_delay)

            # Save the file after we're done
            self.app.save_file()

            self.activity_logger.info("Saved file {file_path}", state="RUNNING", file_path=self.file_path)

class Notepad(BaseApp):
    """Simple text editing with the notepad application"""

    RANDOM_FILENAMES = ["business files", "birthday ideas", "random 1"]
    DEFAULT_DIRECTORY = "%USERPROFILE%\\Documents\\"

    def open(self, command_line_file=""):
        """Start the notepad application"""

        self.command_line_file_opened = False
        self.app = None

        # Check whether the application is already open
        if self.client.app_manager.is_open(self.__class__.__name__):
            self.app = self.client.app_manager.get(self.__class__.__name__)
        else:
            # Otherwise, create the application.
            self.app = Application(backend="uia")

            # If a file is specified, wrap it in quotes
            if command_line_file:
                command_line_file = "\"{}\"".format(command_line_file)

            self.app.start("notepad.exe {}".format(command_line_file))

            # If a command_line_file is specified, we need to check for a prompt
            # that tells us that this file couldn't be opened
            if command_line_file:
                # Assume that it's opened the file on the command line
                self.command_line_file_opened = True

                file_dialog = self.app.top_window().window(title="Notepad")
                if file_dialog.exists():
                    dialog_text = file_dialog.window(auto_id="65535")
                    if dialog_text.exists():
                        text = "".join(dialog_text.texts())
                        if "Couldn't find the" in text:
                            # If this prompt comes up and we've found the error prompt's text, set it to false
                            self.command_line_file_opened = False

                    # Make sure we click the No button
                    file_dialog.window(title="No").click()

            self.client.app_manager.add(self.__class__.__name__, self.app)

        # Get the notepad we've opened and ensure it is visible before we start
        self.notepad = self.app.top_window()
        self.notepad.wait("visible")

        return self.app

    def close(self):
        if self.app is not None:
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

    # TODO: Add parameter which will not attempt to save a new file
    def open_file(self, file_path, attempt_open=False):
        """A method to open a file in notepad, if attempt_open = False then save as a new file.
        Returns the file path that was opened.
        """
        # TODO: Can we improve the save dialog so that if it somehow gets closed, we can safely handle that?

        # Firstly, click new so that we don't save as another file
        try:
            self.notepad.menu_select("File -> New")
        except Exception:
            # Use keyboard instead..
            self.notepad.type_keys("^c^n")

        if not file_path:
            # If attempt_open is True, and file_path is "", we should try and locate a random file we can open (most likely for ReadContent)
            # Otherwise, generate a new filename we can use (most likely for WriteContent)
            if attempt_open:
                # Lets try and find a random file to open
                text_directory = os.path.abspath(os.path.expandvars(self.DEFAULT_DIRECTORY))

                files = []

                # Check for the documents directory
                for file in os.listdir(text_directory):
                    file_path = os.path.join(text_directory, file)
                    # Check whether this is a file or directory
                    if os.path.isfile(file_path):
                        # Basic file extension check
                        if file_path.endswith(".txt"):
                            # Add it to a list of files
                            files.append(file_path)
                
                if len(files):
                    file_path = random.choice(files)
                else:
                    # No file could be found to open, return None
                    return None
            else:
                text_generator = TextGenerator(self.client, max_words=5)

                # If no file path is passed, attempt to generate a random file name
                random_file_name = text_generator.gen_sentence()
                random_file_name = random_file_name.replace(".", "").replace(",", "")

                # Check it's a valid file name
                if not all(char in string.ascii_letters or char == " " for char in random_file_name) or len(random_file_name) > 200:
                    # If it didn't generate a random file name, just use a default one
                    random_file_name = random.choice(self.RANDOM_FILENAMES)

                file_path = self.DEFAULT_DIRECTORY + random_file_name + ".txt"

        if attempt_open:
            self.debug_logger.info("Attempting to access open dialog")

            try:
                self.notepad.menu_select("File -> Open")
            except TimeoutError:
                # now try using Ctrl+O
                self.notepad.send_keys("^c^o")

            # Wait before typing file name
            time.sleep(3)

            # Can't find the open dialog, return None
            if not self.notepad.window(title="Open", control_type="Window").exists():
                return None

            # wait("exists") forces resolution
            # This is required because the "this file can't be found" popup is also named "Open"
            # Otherwise, open_dialog will then fail to resolve because there are 2 identical windows
            # TODO: I'm sure there's a better implementation than this that doesn't require so many
            # calls.
            open_dialog = self.notepad.window(title="Open", control_type="Window").wait("exists")
            
            # Write the file path
            type_keys_into_window(open_dialog.descendants(class_name="Edit")[0], file_path)

            # Wait before clicking open
            time.sleep(1)

            # Luckily for us, the open button has a auto ID of 1
            self.notepad.window(title="Open", control_type="Window").window(auto_id="1", title="Open").click()

            try:
                open_dialog_children = open_dialog.children(title="Open", control_type="Window")
            except ElementNotFoundError:
                # Open dialog has disappeared, assume we've opened it
                return file_path
            else:
                if len(open_dialog_children):
                    file_doesnt_exist_dialog = open_dialog_children[0]

                    # If the file doesn't exist, a dialog pops up with an OK button
                    # If this dialog pops up, we can set attempt_open false
                    file_doesnt_exist_dialog.children(title="OK")[0].click()

                    # Close the open dialog and set file_exists to false, so we can create the file
                    open_dialog.close()

                    attempt_open = False
            
        # If the file doesn't exist, let's save the current file using Save As
        if not attempt_open:
            try:
                self.notepad.menu_select("File -> Save As")
            except Exception:
                # Use keyboard instead..
                self.notepad.type_keys("^c^s")
                
            # Wait before typing file path
            time.sleep(3)

            # Write the file path
            save_as_dialog = self.notepad.window(title="Save As", control_type="Window")

            # if the save as window doesn't pop up, return None, something went wrong...
            if not save_as_dialog.exists():
                return None

            type_keys_into_window(save_as_dialog.window(class_name="Edit"), file_path)

            # Click the save button
            save_as_dialog.window(title="Save").click()

            # Check whether we have a overwrite prompt
            try:
                # Wait before typing setting overwrite
                time.sleep(1)

                # if a file already exists at this directory, a dialog pops up with a Yes/No button.
                save_as_dialog.window(title="Confirm Save As").window(title="Yes").click()

                # Clicking yes automatically closes the open dialog
            except ElementNotFoundError:
                # Yes button was not found, so we successfully saved the new file
                pass
        
        # Return the file path that we opened
        return file_path

    def write_content(self, content, typing_delay=0.08, line_delay=0.1):
        """Writes content into the notepad file.
        Note, the file should be open before attempting to write.
        """
        # TODO: add checks to verify file is open?
        try:
            type_keys_into_window(self.notepad["Edit"], content, typing_delay=typing_delay, line_delay=line_delay)
        except MatchError:
            # If a match error occurs, there is a possiblity the notepad window has been closed
            self.debug_logger.warning("A notepad window was closed unexpectedly, ending write content early")

    def move_cursor_up(self):
        """Moves text cursor up a line in file"""
        self.notepad["Edit"].type_keys("{VK_UP}")

    def move_cursor_down(self):
        """Moves text cursor down a line in file"""
        self.notepad["Edit"].type_keys("{VK_DOWN}")

    def insert_line_above(self, content, typing_delay=0.08, line_delay=0.1):
        """Inserts content above current text cursor"""
        # Press enter and then use arrow keys to move up
        self.notepad["Edit"].type_keys("{ENTER}{VK_UP}")

        # Write content
        self.write_content(content, typing_delay, line_delay)

        # As we're now at the end of the line, pressing right arrow will go to the next line
        self.notepad["Edit"].type_keys("{VK_RIGHT}")

    def delete_current_line(self, line_length):
        """Removes current line"""
        # TODO: Use delete instead, I didn't know that's what the delete key did
        self.notepad["Edit"].type_keys(f"{{VK_RIGHT {line_length}}}{{BACKSPACE {line_length}}}", with_spaces=True, with_tabs=True)

    def save_file(self):
        """Saves the current files"""
        # Save file after we have finished
        # We can save using CTRL+S
        # TODO: Prehaps add the save dialog, although this isn't used by many people
        # Check that the process is alive before sending these keys
        # In the event notepad is randomly closed down, this CTRL+S will just be sent to the next open window
        if self.app.is_process_running():
            keyboard.send_keys("^c^s")

            time.sleep(3)

            # Check whether a prompt warning us about unicode characters has appeared
            if self.notepad.window(title="Notepad").exists():
                self.notepad.window(title="Notepad").window(title="OK").click()

                time.sleep(3)

APPS = ["Notepad"]
TASKS = ["WriteContent", "ReadContent"]
