"""Outlook, to send and read emails within the company
"""

import random
import re
import time
import os
import _ctypes

from pywinauto import Desktop, keyboard
from pywinauto.timings import TimeoutError
from pywinauto.findwindows import ElementAmbiguousError, ElementNotFoundError
from pywinauto.application import Application, AppStartError
from pywinauto.findbestmatch import MatchError
from pywinauto.base_wrapper import ElementNotVisible
from subprocess import Popen
from comtypes import COMError

from apps import BaseApp, BaseTask
from utils import link_check
from utils.pywinauto_text import type_keys_into_window
from utils.text_generator import TextGenerator
from utils.find_executable import get_executable_path

class SendEmail(BaseTask):
    '''Sends an email'''

    def task_load(self, recipients=[], ccs=[], subject="", body="", attachments=[], random_attachment_dir="%USERPROFILE%\\Documents\\", random_attachment_count=0):
        self.app = self.client.modules.get_app("apps.outlook", APPS[0])(self.client)
        self.text_generator = TextGenerator(self.client)
        self.recipients = recipients
        self.ccs = ccs
        # If no subject/body is passed, use text generator
        self.subject = subject if subject else self.text_generator.gen_sentence()
        self.body = body.replace("\\n", "\n") if body else self.text_generator.gen_paragraph()
        self.attachments = attachments

        # Directory where random attachments are found
        self.random_attachment_dir = os.path.abspath(os.path.expandvars(random_attachment_dir))
        # Check that the directory ends in path seperator
        if not self.random_attachment_dir.endswith("\\"):
            self.random_attachment_dir = self.random_attachment_dir + "\\"

        random_url = random.choice(["https://reddit.com", "https://youtube.com", "https://bbc.co.uk"])
        
        # Check whether they want a random URL
        if "[random_url]" in subject or "[random_url]" in body:
            request = self.client.connection.post("/api/resources/browsing", json={
                    "url_count": 1,
                    "url_tags": {"countries": {"$in": ["any", "uk"]}} # TODO: Insert profile logic
                }
            )

            # As we've already seeded random_url, if the request fails, we don't need to do anything else
            if request is not None and request.status_code == 200:
                url_list = request.json()

                if len(url_list):
                    random_url = url_list[0]
            
            # Now replace [random_url] with the random url
            self.subject = self.subject.replace("[random_url]", random_url)
            self.body = self.body.replace("[random_url]", random_url)

        # Number of random attachments to attach
        self.random_attachment_count = random_attachment_count

    def start(self):
        '''Starts/Gets outlook'''
        super().start()

        # Get outlook application
        self.outlook_app = self.app.open()
        self.outlook = self.outlook_app.top_window()
        
    def stop(self):
        '''Ends outlook'''
        super().stop()

    async def main(self):
        '''Sends an email
        '''
        if not self.recipients:
            # We'll just use a test email
            self.recipients = ["administrator@contoso.com"]
    
        new_email_button = self.outlook.descendants(control_type="Button", title="New Email")
        
        if not len(new_email_button):
            self.debug_logger.warning("Failed to find new email button - attemping shortcut method")
            keyboard.send_keys("^n")
        else:
            new_email_button[0].click()

        # Find the new email window
        message_popout = self.outlook_app.window(title_re=r".* - Message \(HTML\)")

        try:
            message_popout.wait("exists")
        except TimeoutError:
            self.debug_logger.warning("Failed to find popout window for sending an email")
            return

        # TODO: Find a better way to identify form regions instead of descendants
        # Recipients
        for recipient in self.recipients:
            message_popout.descendants(control_type="Edit", title="To")[0].type_keys(recipient + "; ", with_spaces=True, pause=0.05)
            time.sleep(0.3)
        
        # CCs
        for cc in self.ccs:
            message_popout.descendants(control_type="Edit", title="Cc")[0].type_keys(cc + "; ", with_spaces=True, pause=0.05)
            time.sleep(0.3)

        time.sleep(1)

        # Subject field
        message_popout.descendants(control_type="Edit", title="Subject")[0].type_keys(self.subject, with_spaces=True, pause=0.05)

        time.sleep(1)

        # MessagePane - message area
        message_popout.window(auto_id="Body").type_keys(
            self.body,
            with_spaces=True,
            with_newlines=True,
            with_tabs=True,
            pause=0.05)


        time.sleep(3)
        
        # Check whether we have attachments we can attach
        if self.random_attachment_count or len(self.attachments):
            # Start with the attachments passed (convert them to absolute paths)
            attachments = set([os.path.abspath(os.path.expandvars(attachment)) for attachment in self.attachments])

            # Check whether we want to attach any random attachments
            if self.random_attachment_count:
                # Then retrieve additional random attachments
                # Retrieve files from this folder
                files = []
                for file in os.listdir(self.random_attachment_dir):
                    # Check whether this is a file and not a directory
                    if os.path.isfile(os.path.join(self.random_attachment_dir, file)):
                        # desktop.ini seems to cause some problems (is an internal windows file)
                        if file == "desktop.ini":
                            continue

                        # Attach this file
                        files.append(os.path.join(self.random_attachment_dir, file))
                
                # self.random_attachment_count times, add a random file from the random dir
                for _ in range(self.random_attachment_count):
                    # Check there are some files left
                    if len(files):
                        # Pop a random file then add it to the set of attachments
                        attachments.add(files.pop(random.randrange(len(files))))
                
            # Now add attachments
            for attachment in attachments:
                if self.add_attachment(message_popout, attachment):
                    self.activity_logger.info("Added attachment {attachment} to email", state="RUNNING", attachment=attachment)
                else:
                    self.activity_logger.warning("Failed to add attachment {attachment} to email", state="RUNNING", attachment=attachment)

        # Hit the Send button
        #message_popout.window(title="Send", class_name="Button").click()
        # TODO: I can't seem to find the button, so let's use Alt-S to send the email
        # The one above doesn't seem to work?
        message_popout.type_keys("%s")

        time.sleep(3) # wait for email to send
        
        # Check for prompt about forgetting to include an attachment
        try:
            message_popout.child_window(title="Attachment Reminder").child_window(title="Send Anyway").click()

            time.sleep(3)
        except ElementNotFoundError:
            # No prompt, just continue
            pass
        
        # Now check for the prompt that warns these files are "unsafe"
        try:
            message_popout.child_window(title="Microsoft Outlook").child_window(title="Yes").click()

            time.sleep(3)
        except ElementNotFoundError:
            # No prompt, just continue
            pass
        
        # Set focus of outlook window
        self.outlook.set_focus()

    def add_attachment(self, message_popout, file_path):
        """This function will add a file to the email. Returns true if the file was successfully attached or
        false if it was not."""
        try:
            # Click attach file
            message_popout.child_window(title="Attach File...", control_type="MenuItem").expand()

            # Then click browse PC
            message_popout.child_window(title="Attach File...", control_type="MenuItem").child_window(control_type="MenuItem", title="Browse This PC...").invoke()

        except ElementNotFoundError:
            # Can't find the menu, skip the attachments
            return False
        else:
            time.sleep(3)

            # If the popup hasn't appeared, return early
            if not message_popout.window(title="Insert File").exists():
                return False

            # Type the file path into the insert bar
            type_keys_into_window(message_popout.window(title="Insert File").window(class_name="Edit"), file_path)

            time.sleep(2)

            # Then press Open to attach the files
            message_popout.window(title="Insert File").window(title="Open", class_name="Button").click()

            # Check whether the file did exist
            try:
                # When the file doesn't exist, the Insert File dialog spawns another Insert File dialog
                # Therefore, if our search returns 2 windows called "Insert File", we know the file doesn't exist
                # There's likely a better way of searching this
                message_popout.window(title="Insert File").wait("exists")
            except ElementAmbiguousError:
                return False
            except TimeoutError:
                # If we've timed out, it means that the prompt has closed already (and no additional one was spawned, so we're good to go!)
                pass

            time.sleep(2)

        return True

class ReadEmail(BaseTask):
    '''Browses some emails'''

    DOWNLOADS_DIRECTORY = "%USERPROFILE%\\Downloads\\"

    def task_load(self, reply_body="Default Reply", reply_percentage_chance=10, open_url_chance=50):
        self.app = self.client.modules.get_app("apps.outlook", APPS[0])(self.client)
        self.reply_body = reply_body.replace("\\n", "\n")
        self.reply_percentage_chance = reply_percentage_chance
        self.open_url_chance = open_url_chance

    def start(self):
        '''Starts/Gets outlook'''
        # As per schema, call super().start() at the start of the task
        super().start()

        # Get the outlook application
        self.outlook_app = self.app.open()
        self.outlook = self.outlook_app.top_window()


    def stop(self):
        '''Ends outlook'''
        # As per schema, call super().stop() at the end of the task
        super().stop()

    def email_length(self):
        '''Gets how many words in currently viewed email'''
        # start a timer
        start_time = time.time()

        # get the email message content
        try:
            # Retrieve the body element
            body = self.outlook.window(auto_id="Body").parent()

            # Get the text
            text = body.texts()[0]
        except (IndexError, ElementNotFoundError):
            return 10, 0 # error occurred therefore return set value

        # split where there is a \n, \r, space or other unwanted characters
        text = re.split(" |\r|\n|\x0b|\x07", text)

        # end timer and return length and time
        total_time = time.time() - start_time
        return len(text), total_time

    def reply_to_email(self):
        '''
        Sends a reply to currently selected email
        '''
        self.outlook.descendants(control_type="Button", title="Reply")[0].click()
        time.sleep(3)
        
        self.activity_logger.info("Replying to an email", state="RUNNING")

        # Check whether the reply has popped out (for some reason?)
        popout_reply = self.outlook_app.window(title_re="RE: .*")

        if popout_reply.exists():
            reply_window = popout_reply
        else:
            reply_window = self.outlook

        type_keys_into_window(reply_window.window(title="Form Regions").window(auto_id="Body"), self.reply_body)

        time.sleep(3)

        # Hit send
        reply_window.descendants(control_type="Button", title="Send")[0].click()
        time.sleep(5) # wait for email to send

    def scroll_email(self, timeout):
        '''Scrolls email object'''
        try:
            message = self.outlook.window(auto_id="Body")
        except ElementNotFoundError:
            # If we can't find the element, just wait timeout
            time.sleep(timeout)
            return

        end = time.time() + timeout
        while time.time() <= end:
            random_action = random.randint(1, 15)
            if random_action <= 1:
                for _ in range(3):
                    try:
                        message.type_keys("{DOWN}")
                    except ElementNotFoundError:
                        # Body has disappeared? Skip scrolling through this email
                        return
            else:
                time.sleep(0.1)
            
            time.sleep(0.1)

    def get_valid_link_from_email(self):
        """Returns a link that could be opened within the email."""
        try:
            message_body = self.outlook.window(auto_id="Body")

            # Find hyperlinks within the body of the email
            link_elements = message_body.descendants(control_type="Hyperlink")
        except ElementNotFoundError:
            # Can't find the message body, let's just carry on
            return None

        links = []

        for link in link_elements:
            # Get properties of this link control type
            url = link.legacy_properties().get("Value", "")
            # Check whether the URL is valid before adding it to a list of links to pick from
            if link_check.is_link(url) is not None:
                links.append(url)

        # No links to pick from, return false
        if not len(links):
            return None

        return random.choice(links)
    
    # This function is async as it can cause interrupts (i.e. opening attachments)
    async def save_attachments_and_open_them(self):
        """Checks for attachments within an email and saves it. Returns a list of tasks that open the attachments if
        their file type is supported."""

        if self.outlook.window(title="Expand Header").exists():
            self.outlook.window(title="Expand Header").click()
            
            time.sleep(2)

        try:
            attachments = self.outlook.window(title="Form Regions").window(class_name="NetUIOlkAttachmentViewer").children(class_name="NetUIAttachmentItemButton")
        except ElementNotFoundError:
            # The attachment container could not be found
            return []
            
        # Check whether there are any attachments
        if not len(attachments):
            return []
        
        # Now check whether any of the button wrappers that have been returned contain files which we are aware of how to open
        # button.texts() returns ['Employee_Notice.docx 15 KB 1 of 1 attachments']
        # Therefore we can use regex to get the file name, because there's no way to just get the file name
        SUPPORTED_FILE_EXTENSIONS = {
            "docx": {"module":"apps.word", "name":"ReadContent"},
            "pdf": {"module":"apps.acrobat", "name":"ReadContent"},
            "txt": {"module":"apps.notepad", "name":"ReadContent"}
        }

        interrupt_tasks = []

        for attachment_button in attachments:
            texts = attachment_button.texts()
            
            # No text inside the button? Skip it
            if not len(texts):
                continue
            
            attachment_info = texts[0]
            regex_match = re.match(r"(.*)? [\d]* .* [\d]* of [\d]* attachments", attachment_info)

            # Check whether we have a match (i.e. this is a valid attachment)
            if regex_match:
                file_name = regex_match.group(1)

                # Get the final extension, avoids things such as randomfile.exe.txt
                file_extension = file_name.rsplit(".", 1)[-1]

                # Now save the file
                # now we click on the attachment button, which brings up an "Attachment" menu at the top
                # Note that attachment_button actually contains 2 buttons, one is the context menu and one
                # is a button which displays a preview. We actually want to display the preview, which
                # causes the attachment menu at the top to appear.
                # I did attempt to use the context menu, but the context menu seems impossible to interact
                # with inside the client. It can be interacted with via the python interpreter, but when trying
                # to interact with it inside SUS client, I can't find a way to identify it.
                
                # Find the button that isn't named "Attachment options"
                preview_button = None
                for button in attachment_button.children():
                    if "Attachment options" not in button.element_info.name:
                        preview_button = button
                
                # If we can't find the button, just skip it
                if preview_button is None:
                    continue
                
                # Now click this button
                preview_button.click()
                
                # Now let's find the back button
                back_button = self.outlook.window(title="Back to message")
                if not back_button.exists():
                    # Back button doesn't exist, assume our preview fialed to load
                    # In which case we can just go to the next attachment
                    self.debug_logger.warning("Failed to preview attachment {file_name}, skipping it", file_name=file_name)
                    continue

                time.sleep(3)

                # Now we find the save as button
                save_as_button = self.outlook.window(class_name="NetUIRibbonButton", title="Save As")

                if not save_as_button.exists():
                    # Now we must click the back button, which takes us back to the body of the message
                    # rather than the preview.
                    back_button.click()
                    continue

                # Click save as
                save_as_button.click()

                save_as_window = self.outlook.window(title="Save Attachment")

                # If no context_menu appears after 5 seconds, continue onwards to the next attachment
                try:
                    save_as_window.wait("exists", timeout=5)
                except TimeoutError:
                    # Now we must click the back button, which takes us back to the body of the message
                    # rather than the preview.
                    back_button.click()
                    continue
                
                # Wait a little before typing into the box
                time.sleep(3)

                # Handle the save_as_window
                self.handle_attachment_save_as(save_as_window)

                # Check whether a prompt has come up about an error saving the file
                time.sleep(3)
                if self.outlook.window(title="Microsoft Outlook").exists():
                    # Prompt has come up, just press OK and continue on  as usual
                    self.outlook.window(title="Microsoft Outlook").child_window(title="OK").click()

                    # Log error and carry on
                    self.activity_logger.warning("Attempted to save attachment {file_name} but an Outlook error has occured", state="RUNNING", file_name=file_name)

                    # Click back
                    back_button.click()

                    # Wait and continue onwards
                    time.sleep(3)
                else:
                    self.activity_logger.info("Saved attachment {file_name} to the Downloads directory", state="RUNNING", file_name=file_name)

                    # File has saved, click the return to message button before continuing
                    back_button.click()

                    # Now that the file is saved, check whether we can open it
                    time.sleep(3)

                    # Check whether the file extension is in our supported extensions
                    if file_extension in SUPPORTED_FILE_EXTENSIONS:
                        self.activity_logger.info("Running {task} to open attachment {file_name} from the Downloads directory", state="RUNNING", task=".".join(SUPPORTED_FILE_EXTENSIONS[file_extension].values()), file_name=file_name)

                        # TODO: Will the user always open every single attachment they can?
                        # TODO: a "default" task to try opening unknown extensions with - i.e. notepad -
                        # maybe make it optional, so only if "open_unsupported" is passed or something

                        # Create task related to this file extension
                        task = self.client.modules.get_task(**SUPPORTED_FILE_EXTENSIONS[file_extension])
                        file_path = os.path.abspath(os.path.expandvars(self.DOWNLOADS_DIRECTORY + file_name))
                        config = {"file_path": file_path, "time": 120, "add_file_path_to_command_line": True}
                        task_obj = task(self.client, activity_name=self.activity_name, **config)
                        
                        # Now open this attachment
                        await self.client.scheduler.interrupt(task_obj)

    def handle_attachment_save_as(self, save_as_window):
        """Handle the Save As window for saving attachments."""

        # Type file path into edit window (save path)
        # We don't need to write the file extension as this is already handled by the file prompt
        # When the prompt spawns, the edit window already contains the file name, so we can reuse this
        file_path_window = save_as_window.window(class_name="Edit")
        file_name = file_path_window.get_value()

        # Type path into window
        type_keys_into_window(file_path_window, self.DOWNLOADS_DIRECTORY + file_name)
        
        # Now hit Save!
        save_as_window.window(title="Save").click()

        # Now we need to check whether the overwrite prompt has appeared
        try:
            confirm_save_as_window = save_as_window.window(title="Confirm Save As").wait("exists", timeout=5)
        except TimeoutError:
            # We can assume the file has saved, exit
            return self.DOWNLOADS_DIRECTORY + file_name
        
        # Wait before pressing yes
        time.sleep(3)

        # Overwrite the file
        try:
            confirm_save_as_window.children(title="Yes")[0].click()
        except IndexError:
            self.debug_logger.warning("Failed to find Yes button on Confirm Save As dialog - attemping shortcut method")
            # Send ALT-Y
            confirm_save_as_window.send_keys("%y")

        # Return the file path saved
        return self.DOWNLOADS_DIRECTORY + file_name


    async def main(self):
        '''Main email function'''
        # Scroll through emails until timer has finished
        while not self.timer:        
            # Get inbox list
            table_view = self.outlook.window(class_name="SuperGrid")

            found_emails = True

            # While the timer is still running
            try:
                # For each email in the list
                emails = table_view.descendants(control_type="DataItem")

                if not len(emails):
                    found_emails = False
            except ElementNotFoundError:
                found_emails = False

            if not found_emails:
                # No emails were found to browse, just wait
                self.activity_logger.info("Found no emails to browse, waiting for 45 seconds", state="RUNNING")
                time.sleep(45)
            else:
                # Iterate through each email
                for email in emails:
                    # Click on the email
                    # This is done 3 times as sometimes outlook just refuses to open the email
                    # Particular edge case that I can't reproduce :( - only seen on one email
                    # Doing it 3 times doesn't hurt
                    try:
                        email.click_input()
                        email.click_input()
                        email.click_input()
                    except RuntimeError:
                        pass

                    try:
                        # TODO: I don't like using auto IDs, especially these ones which seem quite "random",
                        # but there isn't a quick way of retrieving these. Another method would be do to
                        # Form Regions.children() and search for child.element_info.name == "Subject" or "From"
                        from_field = self.outlook.window(title="Form Regions").window(auto_id="4292").texts()
                        subject_field = self.outlook.window(title="Form Regions").window(auto_id="4294").texts()
                        self.activity_logger.info("Reading email {subject_field} from {from_field}", state="RUNNING", subject_field=";".join(subject_field), from_field=";".join(from_field))
                    except (MatchError, ElementNotFoundError):
                        # Failed to locate the title, just report we're reading one but can't find the subject
                        self.activity_logger.info("Reading an email - unable to identify subject and recipient", state="RUNNING")

                    # Get the length of the email and time taken to calculate
                    email_length, total_time = self.email_length()

                    # Calculate sleep time based on average reading wpm of 250 (can be added to profiles)
                    # Adjusted for time taken to calculate length of email
                    reading_speed = 250
                    sleep_time = email_length * (60/reading_speed) - total_time
                    if sleep_time < 0:
                        sleep_time = 0

                    # Scroll through email
                    self.scroll_email(sleep_time)
                    
                    # Check for links
                    email_url = self.get_valid_link_from_email()
                    if email_url is not None:      
                        if random.randint(0, 100) < self.open_url_chance:
                            # Create a browse website task and then interrupt the scheduler with it
                            task = self.client.modules.get_task("apps.browser", "BrowseWebsite")
                            # TODO: Is there a better way than doing random.choice? Maybe something linked to profiles?
                            config = {"url_list": [email_url], "time": 180, "use_browser": random.choice(["Chrome", "Firefox", "Edge"]), "max_depth": 15, "add_url_to_command_line": True}
                            task_obj = task(self.client, activity_name=self.activity_name, **config)
                            
                            self.activity_logger.info("Running apps.browser.BrowseWebsite top open {email_url} from email", state="RUNNING", email_url=email_url)
                            
                            # Now open the link 
                            await self.client.scheduler.interrupt(task_obj)
                            
                    # Download and run attachments if they're supported
                    # await as it can cause interrupts
                    await self.save_attachments_and_open_them()

                    # reply to email
                    if random.randint(0, 100) < self.reply_percentage_chance:
                        self.reply_to_email()
                
                # If we've reached here, it means we've iterated through all the emails currently on the page, so we either need to scroll
                # down to the next page
                # or scroll back to the top
                try:
                    # Attempt to retrieve the current scroll percentage
                    currently_scrolled = table_view.iface_scroll.CurrentVerticalScrollPercent
                except Exception as error:
                    # If it fails, just assume we've scrolled to the end
                    currently_scrolled = 100
                    
                # If we're near the end, scroll to the top
                # However, we also need to make sure that at some point, they return to the top of their emails, just to check
                # their new emails.
                # Lets give them a 25% chance for now, this could be linked to personality later
                if currently_scrolled > 95 or random.randint(0, 3) == 3:
                    # Before starting, scroll to the top of the email list (i.e. our latest emails)
                    self.outlook.window(class_name="SuperGrid").scroll("up", "page", count=10)
                else:
                    # Otherwise, just scroll down
                    table_view.scroll("down", "page")

    
    def switch_in(self):
        """Gets focus on the window"""
        self.outlook.set_focus()

        super().switch_in()

    def switch_out(self):
        super().switch_out()

class Outlook(BaseApp):
    '''Simple email with outlook'''

    TASKS = {"ReadEmail": ReadEmail, "SendEmail": SendEmail}

    def open(self):
        '''Start outlook'''
        
        if self.client.app_manager.is_open(self.__class__.__name__):
            self.app = self.client.app_manager.get(self.__class__.__name__)
        else:
            self.app = Application(backend="uia")
            self.app.start(get_executable_path("Outlook", match_case=True))

            # Sometimes there is a prompt about starting Outlook in safe mode.
            # NOTE: To force this error to occur, do app.start(r"C:\Program Files\Microsoft Office\root\Office16\OUTLOOK.EXE"); app.kill()
            time.sleep(5)
            if self.app.window(title="Microsoft Outlook").exists():
                self.app.window(title="Microsoft Outlook").window(title="OK").click()
            
            # There's also a prompt about getting help with an issue starting office
            time.sleep(3)
            if self.app.window(title="Microsoft Outlook").exists():
                self.app.window(title="Microsoft Outlook").window(title="No").click()
            
            time.sleep(3)
            if self.app.top_window().exists():
                if self.app.top_window().window(title="Choose Profile").exists():
                    self.app.top_window().window(title="Choose Profile").window(title="OK").click()

            # Firstly, we wait for 40 seconds for the Inbox - ... - Outlook window
            # If this doesn't appear within 40 seconds, we can then wait for the setup window to appear
            self.outlook = self.app.window(title_re=r"(Inbox - ).*( - .*Outlook)")
            try:
                self.outlook.wait("exists", timeout=60)

                # Check whether there is a security prompt we need to interact with, short timeout as
                # it may not always appear and we don't want to hang forever waiting for it
                self.accept_security_prompt(timeout=10, log_error=False)
                
                # If it exists, then we can return it
                # Set focus of outlook window
                self.outlook.set_focus()

                self.ignore_office_sign_in()

                # Add to app manager
                self.client.app_manager.add(self.__class__.__name__, self.app)

                return self.app
            except TimeoutError:
                # Otherwise, we can assume that we haven't set this up before
                pass

            if not self.login():
                self.debug_logger.error("Failed to retrieve Outlook setup window / setup Outlook")
            else:
                self.activity_logger.info("Successfully setup Outlook for the first time", state="START")

            # After outlook has been setup, reconnect the app
            self.app.connect(title_re=r"(Inbox - ).*( - .*Outlook)")

            self.outlook = self.app.window(title_re=r"(Inbox - ).*( - .*Outlook)")

            self.ignore_office_sign_in()

            # Add to app manager
            self.client.app_manager.add(self.__class__.__name__, self.app)
    
        return self.app

    def ignore_office_sign_in(self):
        time.sleep(10)

        # We face this issue when using not having a license
        sign_in_window = self.outlook.children(control_type="Window", title="Sign in to set up Office")
        time.sleep(3)

        if len(sign_in_window):
            sign_in_window[0].close()
        
        time.sleep(5)
        # Check for privacy window as well
        privacy_prompt = self.outlook.children(title="Your privacy option", control_type="Window")
        
        if len(privacy_prompt):
            privacy_prompt[0].descendants(title="Close")[0].click()

        time.sleep(5)

        # Check for multiple privacy windows
        privacy_prompt = self.outlook.child_window(title="Microsoft respects your privacy", class_name="NUIDialog")
        
        if privacy_prompt.exists():
            privacy_prompt.window(title="Next").click()

            time.sleep(5)

        privacy_prompt = self.outlook.child_window(title="Getting better together", class_name="NUIDialog")
        
        if privacy_prompt.exists():
            privacy_prompt.window(title="No, don't send optional data").click()
            
            time.sleep(1)

            privacy_prompt.window(title="Accept").click()

            time.sleep(5)

        privacy_prompt = self.outlook.child_window(title="Powering your experiences", class_name="NUIDialog")

        if privacy_prompt.exists():
            privacy_prompt.window(title="Done").click()

            time.sleep(5)
        
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


        # Then remove it from the app manager
        self.client.app_manager.remove(self.__class__.__name__)

    def login(self):
        '''Logs into the app'''
        # TODO: Update this application to the new schema using self.app, rather than Desktop wherever possible
        # This requires debugging on Azure where the client will connect via Exchange.
        desktop = Desktop(backend="uia")

        self.debug_logger.info("Starting login process for Outlook")

        # Find the Welcome to Outlook window
        # Now, this window changes depending on the installation type, so we need to detect what
        # type of installation this is (not exactly sure on the installation types though!)
        o365_setup = False

        setup_window = desktop["Welcome to Outlook"]

        # If it doesn't exist after 60 + 40 seconds, it probably isn't going to popup
        # In my testing experience, it takes about 35 seconds to appear
        try:
            setup_window.wait("exists", timeout=60)

        except TimeoutError:
            # Now because we can't find this type, we should now check for the other type
            o365_setup = True

        if o365_setup:
            # Attempt another setup
            setup_window = desktop["Email Account Setup"]

            try:
                setup_window.wait("exists", timeout=60)

            except TimeoutError:
                # If we get here, then we're in trouble!
                self.debug_logger.warning("Failed to setup prompt for Outlook")
                return False

        # Sometimes accounts take a while to load...
        time.sleep(30)
        
        try:
            # Click the connect button (the email is automatically entered from the account login)
            setup_window.child_window(best_match='Connect').click()
        except _ctypes.COMError:
            # If the connect button isn't clickable, we can press back space and manually type in the email
            keyboard.send_keys("{{BKSP}}{}.{}@{}".format(*self.client.profile["credentials"].values(), self.client.profile["active_directory_domain"]))

            # Click the connect button (the email is automatically entered from the account login)
            setup_window.child_window(best_match='Connect').click()
            
        # Wait
        time.sleep(5)

        # Setup an Exchange account
        setup_window.child_window(best_match='Exchange').click()

        # Accept security prompt
        # Although we distribute certificates via GPO, it's a good idea just to check in case
        self.accept_security_prompt(timeout=30, log_error=False)

        # Wait for the finished screen
        if o365_setup:
            ok_button = setup_window.child_window(best_match='Done')
        else:
            ok_button = setup_window.child_window(best_match='OK')

        try:
            # In my testing experience, it appears after about 45 seconds
            ok_button.wait("exists visible", timeout=90)
        except TimeoutError:
            self.debug_logger.error("Failed to find finishish screen for Outlook login")
            return False

        # Now disable setup outlook on my phone (checkbox) and press OK
        setup_window.child_window(best_match='Outlook Mobile on my phone').toggle()

        ok_button.click()
        time.sleep(20)

        # Outlook should now be setup and visible
        return True

    def accept_security_prompt(self, timeout=90, log_error=False):
        # TODO: Update this application to the new schema using self.app, rather than Desktop wherever possible
        # This requires debugging on Azure where the client will connect via Exchange.

        desktop = Desktop(backend="uia")
        self.debug_logger.info("Searching for security prompt", timeout=timeout)

        # Now there will be a security prompt about the certificate because we don't have a valid certificate on the mail server
        # let's find it and click yes we allow it
        security_prompt = desktop["Security Alert"]

        try:
            # In my testing experience, it appears after about 15 seconds
            security_prompt.wait("exists", timeout=timeout)
        except TimeoutError:
            if log_error:
                self.debug_logger.error("Failed to find security prompt for login")
            return False

        # Wait
        time.sleep(3)

        self.debug_logger.info("Found security prompt for Outlook login and pressing OK")

        # Click yes on the security prompt
        security_prompt.child_window(best_match='Yes').click()

        return True
        

APPS = ["Outlook"]
TASKS = ["ReadEmail", "SendEmail"]
