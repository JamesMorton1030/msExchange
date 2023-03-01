from apps import BaseApp, BaseTask
from utils import wexpect
import random
import time
import os
import zlib
import base64
import re
from apps.notepad import Notepad
# A limitation with wexpect is that we use expect("string") to determine
# when we should stop reading from the console and carry on with the script.
# Usually, the > character is expected as this is what will appear in the console
# when it's finished, however if a command outputs a > somewhere, for example the
# dir command will list directories with a <DIR>, the output will be cut off.

# Therefore, whenever we cd, we can use the current working directory as a basis for the 
# prompt, like: C:\Users\AUS> as we know this line is displayed when requesting the next 
# input (i.e. the command has finished). However, there is an extremely rare case where a 
# program may output something identical to this, so there should be some care in how you
# define your expect prompts.

# TODO: How should we manage storing what project we're currently working on?
# Some sort of local storage area?
project_folder = os.path.expanduser(r"~\Documents\Projects")
current_project_path = ""
#current_project_path = r"C:\Users\control\Documents\Projects\lua_lua"


# TODO add logging


#NOTE: these are all tasks because it means you can define specific activities for specific people on the frontend - i.e.
#jeff is working on a specific project, so he always does GitSwapProject to "Jeffs_project", then git pull on it, then works on it


# TODO right now this is directly using notepad and commandline,
# switch to using self.client.scheduler.interrupt to run new tasks instead


class GitPull(BaseTask):
    """Runs git pull on the ."""

    def task_load(self, project_path=""):
        self.app = self.client.modules.get_app("apps.commandline", APPS[0])(self.client)

        if not project_path:
            global current_project_path
            self.project_path = current_project_path
        else:
            self.project_path = project_folder

    def start(self):
        super().start()
        # Initialise command line.
        self.app.start()
        
    def stop(self):
        super().stop()

    def switch_in(self):
        """Gets focus on the window"""
        pass

    async def main(self):
        # Firstly CD to the project directory

        if not self.app.change_directory(self.project_path):
            # TODO debug warning message here or something
            return

        # Now run git pull command

        # Now that we are also aware of our current directory, we can use this to create
        # our cmd prompt string.
        cmd_prompt = self.project_folder + ">"
        self.app.send_line("git pull")
        self.app.process.expect(cmd_prompt)

class GitCommit(BaseTask):
    """Runs git add *, git commit -m "" using the passed config to define the commit message"""

    def task_load(self, project_path=""):
        self.app = self.client.modules.get_app("apps.commandline", APPS[0])(self.client)

        if not project_path:
            global current_project_path
            self.project_path = current_project_path
        else:
            self.project_path = project_folder

    def start(self):
        super().start()
        self.app.start()
        self.notepad = Notepad(self.client)

    def stop(self):
        super().stop()

    async def main(self):
        global current_project_path
        global project_folder

        # Retrieve the commit from API
        strict_commit = True

        if not current_project_path:
            # Call add new project as we don't currently add a project
            current_project_path = "result of call"
            print("not implemented")
        
        # TODO: Actually change the directory when moving this into commandline.py
        # so we can execute the git commit command.

        while not self.timer:
            # TODO: Catch status codes from the request which indicate status

            response = self.client.connection.request("get","/api/programming/{}/commit".format(self.client.username))
            #print(response.status_code)
            commit = response.json()
            
            # TODO
            # Handle 204 on /commit
            # This means there are no more commits
            # so, call /newrepo and then redo commit
            # If /newrepo returns 204 ,then quit - since there are no more repos
            #
            # GIT Pull task:
            # Check whether we have the repo cloned
            # If we do, move into it and call git pull
            # If not, create the folder (in the future, clone this as other people may have changed this, but not thise time because 1 person per repo)
            #
            # GIT Push task
            # (Not necessary yet because no remote server atm)
            # 
            # GIT Commit:
            # Make them commit
            #
            # swapping repos task (random task)
            # call to /swaprepo, doesn't require a repo to be chosen

            # Check whether directories already exist
            # TODO: Move this to command line or find a better way of doing it? UI automation seems almost impossible
            # TODO: Find a better way to change the file seperators
            # NOTE: If they already have a slash in file name, the only safe way to do it is to replace the backslashes with forward slashes
            # and vice versa

            #
            # TODO: Exit on time executed or n commits
            for delta in commit["deltas"]:
                if "/" in delta["path"]:
                    delta["path"] = delta["path"].replace("/", "\\")

                file_path = os.path.join(current_project_path, delta["path"])

                if delta["type"] == "DELETE":
                    print("DELETE FILE: TODO Implement. Use the command line task?")
                    os.remove(file_path)
                else:
                    # Take the data parameter, decode it from base64, then encode to binary and then use zlib to decompress it
                    commit_data = zlib.decompress(base64.b64decode(delta["data"])).decode()
                    # Replace \n or \r\n to \r\n
                    # TODO: Deal with the implicit conversion to windows, should this be an argument?
                    # TODO: Try using ENTER instead?
                    commit_data = re.sub("\r?\n", "\r\n", commit_data)
                    # NOTE: DOes this break the diffs? Strict checking etc.

                    # Ignore the final element since this is the file name
                    directories = []
                    for subdirectory in delta["path"].split("\\")[:-1]:
                        # Check whether this folder already exists
                        if not os.path.exists(os.path.join(current_project_path, *directories, subdirectory)):
                            # If not, create it
                            os.mkdir(os.path.join(current_project_path, *directories, subdirectory))

                    if delta["type"] == "ADD":
                        self.notepad.write_content_to_file(file_path, commit_data, False)
                    elif delta["type"] == "MODIFY":
                        diff_lines = commit_data.split("\r\n")
                    
                        # Open this file and assume it exists since we're modifying
                        self.notepad.open_file(file_path, True)
                        
                        for line in diff_lines:
                            prefix = line[:2]
                            data = line[2:]

                            # TODO: Implement strict commit properly lmao
                            if prefix == "  ":
                                self.notepad.move_cursor_down()
                                # If strict commit is true, verify that the line is the same as the line currently in the file
                                #if data != edit.get_line(line_num):
                                #    print("Line {} doesn't match git commit.".format(line_num))
                            elif prefix == "- ":
                                # Navigate to the end of the line and backspace all these characters
                                self.notepad.delete_current_line(len(data) + 1)
                            elif prefix == "+ ":
                                # Write the line
                                self.notepad.insert_line_above(data)
                        
                        # Save file
                        self.notepad.save_file()
        
            # Run git commit
            # The lines below have to be configured before any commits can be done.
            # git config --global user.email "you@example.com"
            # git config --global user.name "Your Name"

            self.app.change_directory(current_project_path)
            self.app.send_line("git commit -m \"{}\"".format(commit["message"]))
            self.app.process.expect(current_project_path + ">")

        # Close down notepad
        self.notepad.app.kill()




class GitSwapProject(BaseTask):

    def task_load(self, project_path=""):
        self.app = self.client.modules.get_app("apps.commandline", APPS[0])(self.client)

        if not project_path:
            global current_project_path
            self.project_path = current_project_path
        else:
            self.project_path = project_folder

    def start(self):
        super().start()
        # Initialise command line.
        self.app.start()

    def stop(self):
        super().stop()

    # TODO: optional forced parameter for what repo to swap to
    async def main(self):
        response = self.client.connection.request("post","/api/programming/{}/changerepo".format(self.client.username))

        if response.status_code == 204:
            return

        new_repo = response.json()["new_repo"].replace("/","_")

        # TODO: Please stop hard coding these
        current_project_path = os.path.join(project_folder, new_repo)

        # TODO for all of these - more stringent error code checking?

class GitNewProject(BaseTask):
    """
        This task will add you to a new git repo to work on. If your version of the repo doesn't exist yet, 
        it will create the folder and do git init. If it 
        does exist, it will just set the current_project_path to that directory.
    """

    def task_load(self, project_path=""):
        self.app = self.client.modules.get_app("apps.commandline", APPS[0])(self.client)

        if not project_path:
            global current_project_path
            self.project_path = current_project_path
        else:
            self.project_path = project_folder

    def start(self):
        super().start()
        # Initialise command line.
        self.app.start()
     
    def stop(self):
        super().stop()
   
    def switch_in(self):
        """Gets focus on the window"""
        pass
    
    async def main(self):
        response = self.client.connection.request("post","/api/programming/{}/newrepo".format(self.client.username))

        print(response.status_code)
        if response.status_code == 204: # no new repos
            return
        # TODO consider having the scheduler not continue after a task fails - 
        # this task can fail if there are no new repos, in that case do not bother to do any of the following tasks

        new_repo = response.json()["new_repo"].replace("/","_")

        # Firstly go to the directory of the project folder
        self.app.change_directory(project_folder)

        # format for git repo directory - 
        # replace repo ID / with _, so TechSupportJosh/TestRepo -> TechSupportJosh_TestRepo
        current_project_path = os.path.join(project_folder, new_repo)

        # TODO where to start - for now, lets have all users start from C:\Users\username\Documents 
        if not os.path.isdir(current_project_path):
            # TODO should we hard reset if the folder does exist?
            # TODO change this to C:\Projects?
            self.app.send_line("mkdir \"{}\"".format(new_repo))
            self.app.process.expect(">")
            self.app.change_directory(current_project_path)
            self.app.send_line("git init")
            self.app.process.expect(">")
        
class CommandLine(BaseApp):
    """Enter commands into the command line (cmd.exe)"""

    # Amount of seconds between each character being typed
    default_character_delay = 0.01

    def start(self):
        """Start the command line."""
        # Start process with a timeout of 600 seconds. This means if after expect() is called, the result 
        # is still not found after 600 seconds, an exception will be thrown.
        # TODO: Catch this error?
        # TODO: Better implement failsafe timeout so that this class doesn't crash everything

        self.process = wexpect.spawn('cmd.exe', timeout=600)
        
        # Wait for prompt when cmd becomes ready.
        self.process.expect('>')

        print("done?")
        return 

    # TODO: Also change this to better name
    def send_chars(self, text, character_delay=None):
        """Type characters into the terminal. Passing a delay of 0 will instantly type the line out."""
        character_delay = character_delay if character_delay is not None else self.default_character_delay

        for char in text:
            self.process.send(char)
            time.sleep(character_delay)

    # TODO: Change this to something less ambiguous
    def send_line(self, text, character_delay=None):
        """Type a line into the terminal. This will automatically append the Enter key at the end of the line."""
        
        character_delay = character_delay if character_delay is not None else self.default_character_delay

        # Type the characters and append \r\n to the end of the string.
        self.send_chars(text + "\r\n", character_delay)

    # TODO: Improve this - check whether the path is absolute before changing drive, and check if it is actually a different drive
    def change_directory(self, directory):
        """Call the "cd" console command to change directory. Returns true if successful, false if file is missing."""
        self.send_line("{}".format(directory[:2]))
        self.process.expect(">")
        self.send_line("cd \"{}\"".format(directory))
        self.process.expect(">")
        
        # Check whether the path we tried to navigate to exists.
        if "The system cannot find the path specified" in self.process.before:
            # If the path has failed, handle some sort of error? Not sure yet.
            print("CD Failed: \"{}\".".format(directory))
            return False

        return True

APPS = ["CommandLine"]
TASKS = ["GitPull", "GitSwapProject", "GitNewProject", "GitCommit"]
