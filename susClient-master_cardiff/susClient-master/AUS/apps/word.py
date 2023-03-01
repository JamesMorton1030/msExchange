import random
import time
import string
import os

from pywinauto.application import Application
from pywinauto.timings import wait_until_passes
from pywinauto.timings import TimeoutError
from pywinauto.findbestmatch import MatchError
from pywinauto.findwindows import ElementNotFoundError
from pywinauto.base_wrapper import ElementNotVisible
from pywinauto import keyboard
from comtypes import COMError

from apps import BaseApp, BaseTask
from utils.text_generator import TextGenerator
from utils.pywinauto_text import type_keys_into_window
from utils.find_executable import get_executable_path

from comtypes import COMError

class ReadContent(BaseTask):
    """Opens a file and scrolls through it randomly.
    """

    def task_load(self, file_path="", add_file_path_to_command_line=False):
        self.app = self.client.modules.get_app("apps.word", APPS[0])(self.client)
        self.file_path = file_path
        self.add_file_path_to_command_line = add_file_path_to_command_line

    def start(self):
        """Starts Word application"""
        # As per schema, call super().start() at the start of the task
        super().start()

        # Open the application
        if self.add_file_path_to_command_line:
            self.word_app = self.app.open(command_line_file=self.file_path)
        else:
            self.word_app = self.app.open()

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
                self.word_app.top_window().wheel_mouse_input(wheel_dist=random.randint(-3, 3))
                time.sleep(random.uniform(0.5, 5))

class WriteContent(BaseTask):
    """Writes the given content to a word document - 
       if no content is given, it writes random sentences until time expires
    """

    def task_load(self, content="", file_path="", attempt_open=False, typing_delay=0.08, line_delay=0.1):
        self.app = self.client.modules.get_app("apps.word", APPS[0])(self.client)

        self.content = content
        self.text_generator = TextGenerator(self.client) #so we don't have to re-instantiate it each time

        #NOTE: if you don't pass any content (so it's None), then this will write random sentences until time runs out
        self.file_path = file_path
        self.attempt_open = attempt_open
        self.typing_delay = typing_delay
        self.line_delay = line_delay

        # close_app is hardcoded to true in this file as we cannot easily hook the new window that
        # is created when we want to open a new file. So, by forcing it to close, we know that the
        # initial window that is started is the window we can interact with.

        # If in the future someone wishes to fix this, when save_file occurs:
        # CTRL+N to create a new window
        # Hook this new window using the title_re as Document[0-9] - Word
        # Close down the previous window
        # Update app manager with the new window
        # This may or may not be enough to fix this issue.
        self.close_app = True

    def start(self):
        # As per schema, call super().start() at the start of the task
        super().start()

        # Open the application
        self.word_app = self.app.open()

    def stop(self):
        # As per schema, call super().stop() at the end of the task
        super().stop()

    def switch_in(self):
        # Set the focus of the document
        self.word_app.top_window().set_focus()

        # Unpause the timer
        self.timer.unpause()

    def switch_out(self):
        # Pause our timer when we switch out
        self.timer.pause()

    async def main(self):
        # Firstly open the file
        file_path = self.app.open_file(self.file_path, self.attempt_open)

        if file_path is None:
            self.activity_logger.warning("Attempted to open file {file_path} but something went wrong", state="RUNNING", file_path=self.file_path)
        else:
            self.activity_logger.info("Opened file {file_path} to write content into", state="RUNNING", file_path=self.file_path)
            
            self.file_path = file_path

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

class Word(BaseApp):

    RANDOM_FILENAMES = ["Quarterly_Report", "Employee_Notice", "aaaaaaa"]
    DEFAULT_DIRECTORY = "%USERPROFILE%\\Documents\\"

    def open(self, command_line_file=""):
        # This stores whether the file that was specified in the command line was successfully opened
        self.command_line_file_opened = False

        if self.client.app_manager.is_open(self.__class__.__name__):
            self.app = self.client.app_manager.get(self.__class__.__name__)
            self.word = self.app.top_window()
        else:
            self.app = Application(backend="uia")
            
            # If a file is specified, wrap it in quotes
            if command_line_file:
                command_line_file = "\"{}\"".format(command_line_file)

            # switches /w for new document and /q for no splashscreen have been enabled here
            self.app.start("{} /w /q {}".format(get_executable_path("Word", match_case=True), command_line_file))

            # Check if there is a safe mode prompt
            time.sleep(3)
            if self.app.window(title="Microsoft Word").exists():
                self.app.window(title="Microsoft Word").window(title="No").click()

            time.sleep(5)

            self.word = self.app.top_window()

            # Interestingly, this prompt pops up before any activiation issues...
            # If a command_line_file is specified, we need to check for a prompt
            # that tells us that this file couldn't be opened
            if command_line_file:
                # Assume that it's opened the file on the command line
                self.command_line_file_opened = True

                file_dialog = self.word.window(title="Microsoft Word")
                if file_dialog.exists():
                    dialog_text = file_dialog.window(auto_id="4001")
                    if dialog_text.exists():
                        text = "".join(dialog_text.texts())
                        if "Sorry, we couldn't find your file" in text:
                            # If this prompt comes up and we've found the error prompt's text, set it to false
                            self.command_line_file_opened = False

                            # Make sure we click the OK button
                            file_dialog.window(title="OK").click()
                        
                        # Check for another prompt warning us the last time we tried opening this file, it caused a serious error\
                        elif "The last time you opened" in text:
                            self.command_line_file_opened = False

                            # Make sure we click the No button
                            file_dialog.window(title="No").click()
 
            # We faced this issue on azure on activation issues
            # This closes our activation warning
            time.sleep(15)
            activation_window = self.word.children(title="Microsoft Office Activation Wizard")
            
            if len(activation_window):
                activation_window = activation_window[0]

                close_button = activation_window.descendants(title="Close")
                if len(close_button):
                    close_button[0].click()

            # We face another issue when using o365 pro plus installation
            time.sleep(90)

            sign_in_window = self.word.children(control_type="Window", title="Sign in to set up Office")
            time.sleep(3)
            
            if len(sign_in_window):
                sign_in_window[0].close()
            
            time.sleep(5)

            # Privacy prompt as well
            privacy_window = self.word.children(title="Microsoft respects your privacy")
            
            if len(privacy_window):
                privacy_window[0].window(title="Next").click()
                time.sleep(5)
                # Select sending no diag data
                self.word.window(title="No, don't send optional data").select()
                time.sleep(2)
                # Press accept
                self.word.window(title="Accept").click()

            # Another privacy prompt...
            time.sleep(3)

            privacy_window = self.word.children(title="Your privacy option")
            
            if len(privacy_window):
                time.sleep(3)
                privacy_window[0].descendants(title="Close")[0].click()

            # When initialising word for the first time, there's a prompt asking whether
            # you want to use an ODF file format or XML file format. We'll use the
            # office one. 
            time.sleep(3)
            try:
                # Try and find the welcome window
                # Select the top option
                self.word.child_window(best_match='Welcome to Microsoft Office').child_window(best_match="Office Open XML formats").select()
                # Press OK
                self.word.child_window(best_match='Welcome to Microsoft Office').child_window(best_match="OK").click()
            except (TimeoutError, MatchError, ElementNotFoundError):
                # Couldn't find the window, just carry on
                pass
                
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

        self.client.app_manager.remove(self.__class__.__name__)

    def open_file(self, file_path, attempt_open=False):
        """A method to open a file in word, if attempt_open = False then save as a new file
        It will then check whether each folder exists and if not, creates it and navigates to it.
        """

        if not file_path:
            # If attempt_open is True, and file_path is "", we should try and locate a random file we can open (most likely for ReadContent)
            # Otherwise, generate a new filename we can use (most likely for WriteContent)
            if attempt_open:
                # Lets try and find a random file to open
                documents_directory = os.path.abspath(os.path.expandvars(self.DEFAULT_DIRECTORY))

                files = []

                # Check for the documents directory
                for file in os.listdir(documents_directory):
                    file_path = os.path.join(documents_directory, file)
                    # Check whether this is a file or directory
                    if os.path.isfile(file_path):
                        # Basic file extension check
                        if file_path.endswith(".docx"):
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

                file_path = self.DEFAULT_DIRECTORY + random_file_name + ".docx"

        # We don't need to open a new document here because of the close_app hardcoded
        if attempt_open:
            # Use shortcuts because it's easier than trying to access the windows
            # Send CTRL-O
            keyboard.send_keys("^c^o")

            # Click the open button
            self.word.window(title="Browse").click()
            
            # Wait before typing file name
            time.sleep(5)

            # Now we can enter file name
            type_keys_into_window(self.word.child_window(best_match="Open").child_window(class_name="Edit"), file_path, typing_delay=0.08)

            # Now we can click the open button
            time.sleep(1)
            self.word.child_window(best_match="Open").child_window(title="Open", control_type="SplitButton").click_input()

            time.sleep(2)
            # Now, if the file doesn't exist, a prompt will come up saying "This file does't exist", in which case
            # we then set attempt_open to false and then create the file instead.
            try:
                # TODO: This can be improved, rather than looking for OK, look for
                # the fail dialog
                self.word.child_window(best_match="Open").child_window(title="OK").click()
                self.word.child_window(best_match="Open").close()

                attempt_open = False
            except (ElementNotFoundError, MatchError, COMError):
                # OK button was not found, so hopefully we opened the file.
                pass

            # Now, there's also a prompt about an invalid file prompt
            try:
                # if this first one fails, this means there's no prompt and the file has opened
                self.word.window(title="Microsoft Word").child_window(title="Yes").click()
            except ElementNotFoundError:
                # Prompt wasn't found, file was opened
                pass
            else:
                # This prompt then causes another prompt, for which we'll click yes and return None since that file cannot be opened
                try:
                    self.word.window(title="Microsoft Word").child_window(title="OK").click()
                except ElementNotFoundError:
                    # Word managed to recover the file, continue as normal
                    pass
                else:
                    # File couldn't be opened, return None
                    return None
                
        # If the file doesn't exist, let's save the current file using Save As
        if not attempt_open:
            # Firstly we press escape to ensure that we're on the body view
            self.word.type_keys("{ESC}")
            time.sleep(2)
            # Now we can hit F12 to open the save as dialog (rather handy)
            self.word.type_keys("{F12}")

            # Wait before typing file path
            time.sleep(5)

            # if the save as window doesn't pop up, return None, something went wrong...
            if not self.word.child_window(best_match="Save As").exists():
                return None
            if not self.word.child_window(best_match="Save As").child_window(class_name="Edit").exists():
                return None
                
            # Now we can type the keys into the path
            type_keys_into_window(self.word.child_window(best_match="Save As").child_window(class_name="Edit"), file_path, typing_delay=0.08)

            time.sleep(3)

            self.word.child_window(best_match="Save As").child_window(best_match="Save").click()

            try:
                # Check whether the prompt comes up that check sif you want to overwrite the file
                self.word.child_window(best_match="Save As").child_window(best_match="Microsoft Word").child_window(best_match="OK").click()
            except (TimeoutError, ElementNotFoundError, MatchError):
                # If it hasn't come up, assume that we've opened the file
                pass
        
        # Return the file path that we opened
        return file_path

    def write_content(self, content, typing_delay=0.08, line_delay=0.1):
        """Writes content into the word body.
        Note, the file should be open before attempting to write.
        """
        # TODO: add checks to verify file is open?
        edit_window = self.get_end_page_window()
        # TODO: Do we need to focus this window?

        # When Word reaches the end of a page, it creates a new one as you'd expect
        # However, our original page that we referenced (auto_id="Body") will be the 1st
        # page. However, once this eventaully gets scrolled off screen, we get the 
        # ElementNotFoundError. Therefore, once we get this error, we need to update the body
        # window.

        # Our type_keys_into_window will return a string if ElementNotVisible is raised. Therefore, if we call
        # this function and we get a response that isn't None, we need to update our edit_window and then recall this function with the result
        unwritten_text = type_keys_into_window(edit_window, content, typing_delay=typing_delay, line_delay=line_delay)
        # If the result of this function isn't None
        while unwritten_text is not None:
            # Get the new edit window
            edit_window = self.get_end_page_window()

            # Check we got a result back
            if edit_window is None:
                self.debug_logger.warning("Failed to find the last page of a Word document, exiting early")
                break

            # Then rewrite this text with the updated end window
            unwritten_text = type_keys_into_window(edit_window, unwritten_text, typing_delay=typing_delay, line_delay=line_delay)

    def get_end_page_window(self):
        """This function returns the end page window."""
        pages = self.word.child_window(control_type='Document').children()
        if not len(pages):
            # We found no pages, return None
            return None
        # Luckily children() returns the pages in their expected order, so we can get the last element in the list
        last_page = pages[-1]
        # Now return the actual body element from this child
        edit_window = last_page.children(control_type='Edit')
        # children() returns a list, so check whether it returns something
        if not len(edit_window):
            return None

        # Otherwise, return the first element
        return edit_window[0]

    def save_file(self):
        """Saves the current files"""
        # Save file after we have finished
        # We can save using CTRL+S
        # TODO: Prehaps add the save dialog, although this isn't used by many people
        # Check that the process is alive before sending these keys
        # In the event notepad is randomly closed down, this CTRL+S will just be sent to the next open window
        if self.app.is_process_running():
            keyboard.send_keys("^c^s")

APPS = ["Word"]
TASKS = ["WriteContent", "ReadContent"]
