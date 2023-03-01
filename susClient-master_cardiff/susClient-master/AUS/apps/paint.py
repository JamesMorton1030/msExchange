"""Paint
"""

import time
import random
import string
import pyautogui
import re
import os

from pywinauto.application import Application
from pywinauto.findwindows import ElementNotFoundError
from pywinauto.base_wrapper import ElementNotVisible
from pywinauto import keyboard

from comtypes import COMError

from apps import BaseApp, BaseTask
from utils.pywinauto_text import type_keys_into_window
from utils.text_generator import TextGenerator

class ViewContent(BaseTask):
    """Opens a image file and sleeps until the task timer has finished.
    """

    def task_load(self, file_path=""):
        # TODO: Add support for passing an image via command line argument, like Word
        self.app = self.client.modules.get_app("apps.paint", APPS[0])(self.client)
        self.file_path = file_path

        # TODO: Implement close_app = False support
        self.close_app = True

    def start(self):
        """Starts Paint application"""
        # As per schema, call super().start() at the start of the task
        super().start()

        # Open the paint application
        self.paint_app = self.app.open()

    def stop(self):
        """Saves our file and calls BaseTask stop."""
        # As per schema, call super().stop() at the end of the task
        super().stop()

    async def main(self):
        # Firstly open the file
        if self.file_path == "":
            self.activity_logger.info("Task was called but no file path was provided, attempting to find a picture to open", state="RUNNING")

        # If no file path is passed (and because attempt_open = True) it will attempt to find a random file to open
        file_path = self.app.open_file(self.file_path, attempt_open=True)

        if file_path is None:
            self.activity_logger.warning("Attempted to open file {file_path} but it did not exist, exiting early", state="RUNNING", file_path=self.file_path)
        else:
            self.activity_logger.info("Opened file {file_path} to read through", state="RUNNING", file_path=file_path)

            # There's not too much we can do with viewing pictures, so we'll just sleep..
            while not self.timer:
                time.sleep(random.uniform(10, 30))

class DrawContent(BaseTask):
    """Draws a random set of lines to a image file at file_path (a random file if file_path='')"""

    def task_load(self, file_path="", attempt_open=False):
        self.app = self.client.modules.get_app("apps.paint", APPS[0])(self.client)
        self.file_path = file_path
        self.attempt_open = attempt_open

        # TODO: Implement close_app = False support
        self.close_app = True

    def start(self):
        """Starts paint application"""
        # As per schema, call super().start() at the start of the task
        super().start()

        # Open the paint application
        self.paint_app = self.app.open()

    def stop(self):
        """Saves our file and calls BaseTask stop."""
        # Double check that the paint process is still running
        # In the event it somehow got closed, we need to ensure that we fire close_app so that it's removed from AppManager
        if not self.paint_app.is_process_running():
            self.close_app = True

        # As per schema, call super().stop() at the end of the task
        super().stop()

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

            self.activity_logger.info("Opened file {file_path} to draw content into", state="RUNNING", file_path=self.file_path)

            # Draw lines using pyautogui
            # Firstly identify the canvas size borders
            canvas_container = self.paint_app.top_window().window(class_name="MSPaintView").rectangle()
            # Coordinates (X, Y)
            # Here we add 10 to each of the coordinates as container has some padding before the canvas
            top_left = (canvas_container.left + 10, canvas_container.top + 10)

            # Now we retrieve the current canvas size using this lovely regex:
            # Note the x character in the middle is not an x, but a multiplication sign
            canvas_size = None

            if self.paint_app.top_window().child_window(title_re=r"\d* {} \d*.*px".format(chr(215))).exists():
                # Get that text of the element:
                canvas_text = "".join(self.paint_app.top_window().child_window(title_re=r"\d* {} \d.*px".format(chr(215))).texts())
                # This yields 1152 × 542\u200fpx, which we can extract using regex
                match = re.match(r"(\d*) {} (\d*).*px".format(chr(215)), canvas_text)
                if match:
                    canvas_size = (int(match.group(1)), int(match.group(2)))

            if not canvas_size:
                # Default to some safe canvas sizes..
                canvas_size = (800, 600)
            
            self.debug_logger.info("Found canvas size: {x} x {y}", x=canvas_size[0], y=canvas_size[1])

            bottom_right = (top_left[0] + canvas_size[0], top_left[1] + canvas_size[1])
            
            # Store the colour coordinates
            colours_supported = True

            try:
                # Depending on the language of the OS, it appears the title can be Colours or Colors
                colour_rectangle = self.paint_app.top_window().window(control_type="ToolBar", title_re="Colou?rs").window(title="").rectangle()
                colour_top_left = (colour_rectangle.left, colour_rectangle.top)
                # The bottom row of colours is all white, so just get the top 2 rows
                colour_bottom_right = (colour_rectangle.left + colour_rectangle.width(), colour_rectangle.top + (2 * colour_rectangle.height()) // 3)
            except ElementNotFoundError:
                # If we can't find the toolbar colours window, disable the ability to change colours
                colours_supported = False

            # Move mouse to random coordiante
            pyautogui.moveTo(random.randint(top_left[0], bottom_right[0]),
                     random.randint(top_left[1], bottom_right[1]))

            while not self.timer:
                # Now we draw random lines until the timer is finished!

                # Pick a random point
                random_point = (random.randint(top_left[0], bottom_right[0]),
                     random.randint(top_left[1], bottom_right[1]))

                try:
                    # Draw the line
                    pyautogui.dragTo(*random_point,
                        duration=random.randint(1,10))

                    time.sleep(random.randint(1,5))

                    # Now pick another colour
                    if colours_supported:
                        pyautogui.click(x=random.randint(colour_top_left[0], colour_bottom_right[0]), y=random.randint(colour_top_left[1], colour_bottom_right[1]))

                    time.sleep(random.randint(1,2))

                    # Move mouse back to where we were before picking the colour
                    pyautogui.moveTo(*random_point, duration=1)
                except pyautogui.FailSafeException:
                    # FailSafeException is caused when the mouse is pushed into the corner of the screens, to prevent you being able
                    # to lose control of your program. If we catch this, this probably means someone is debugging it and wishes to exit
                    # out of the program.
                    # Therefore, we'll sleep 90 seconds to give the user plenty of time to exit the program, before carrying on without loop.
                    # If this exception happens naturally (which is unlikely), this means our task will continue on as usual.
                    self.debug_logger.warning("Received FailSafeException from pyautogui, waiting 90 seconds before continuing")
                    time.sleep(90)

            # Save the file after we're done
            self.app.save_file()

            self.activity_logger.info("Saved file {file_path}", state="RUNNING", file_path=self.file_path)

class Paint(BaseApp):
    """Simple image manipulation with mspaint"""

    DEFAULT_DIRECTORY = "%USERPROFILE%\\Pictures\\"
    RANDOM_FILENAMES = ["a beautiful sea", "abstract art", "im bored"]

    def open(self):
        """Start the paint application"""
        # Check whether the application is already open
        if self.client.app_manager.is_open(self.__class__.__name__):
            self.app = self.client.app_manager.get(self.__class__.__name__)
            self.paint = self.app.top_window()
        else:
            # Otherwise, create the application.
            self.app = Application(backend="uia")
            self.app.start("mspaint.exe")

            time.sleep(5)

            self.paint = self.app.top_window()

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

    # TODO: Add parameter which will not attempt to save a new file
    def open_file(self, file_path, attempt_open=False):
        """A method to open a file in Paint, if attempt_open = False then save as a new file.
        Returns the file path that was opened.
        """
        # TODO: Can we improve the save dialog so that if it somehow gets closed, we can safely handle that?

        if not file_path:
            # If attempt_open is True, and file_path is "", we should try and locate a random file we can open (most likely for ViewContent)
            # Otherwise, generate a new filename we can use (most likely for DrawContent)
            if attempt_open:
                # Lets try and find a random file to open
                images_directory = os.path.abspath(os.path.expandvars(self.DEFAULT_DIRECTORY))

                files = []

                # Check for the documents directory
                for file in os.listdir(images_directory):
                    file_path = os.path.join(images_directory, file)
                    # Check whether this is a file or directory
                    if os.path.isfile(file_path):
                        # Basic file extension check
                        if file_path.endswith((".jpg", ".png", ".jpeg")):
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

                file_path = self.DEFAULT_DIRECTORY + random_file_name + random.choice([".jpg", ".png"])

        if attempt_open:
            self.debug_logger.info("Attempting to access open dialog")

            self.paint.type_keys("^c^o")

            # Wait before typing file name
            time.sleep(3)

            # Can't find the open dialog, return None
            if not self.paint.window(title="Open", control_type="Window").exists():
                return None

            # wait("exists") forces resolution
            # This is required because the "this file can't be found" popup is also named "Open"
            # Otherwise, open_dialog will then fail to resolve because there are 2 identical windows
            # TODO: I'm sure there's a better implementation than this that doesn't require so many
            # calls.
            open_dialog = self.paint.window(title="Open", control_type="Window").wait("exists")
            
            # Write the file path
            type_keys_into_window(open_dialog.descendants(class_name="Edit")[0], file_path)

            # Wait before clicking open
            time.sleep(1)

            # Luckily for us, the open button has a auto ID of 1
            self.paint.window(title="Open", control_type="Window").window(auto_id="1", title="Open").click()

            try:
                print("checking for children")
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
            self.paint.type_keys("{F12}")
            
            # Wait before typing file path
            time.sleep(3)

            # Write the file path
            save_as_dialog = self.paint.window(title="Save As", control_type="Window")

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

    def save_file(self):
        """Saves the current files"""
        # Save file after we have finished
        # We can save using CTRL+S
        # TODO: Prehaps add the save dialog, although this isn't used by many people
        # Check that the process is alive before sending these keys
        # In the event paint is randomly closed down, this CTRL+S will just be sent to the next open window
        if self.app.is_process_running():
            keyboard.send_keys("^c^s")

            time.sleep(3)

APPS = ["Paint"]
TASKS = ["DrawContent", "ViewContent"]
