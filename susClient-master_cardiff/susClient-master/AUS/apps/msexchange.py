"""
SUS use of Exchange Server,
Outlook
"""

import random
import re
import time
import os
import _ctypes
import sys

sys.path.append("./utils")

from pywinauto import Desktop, keyboard
from pywinauto.timings import TimeoutError
from pywinauto.findwindows import ElementAmbiguousError, ElementNotFoundError
from pywinauto.application import Application, AppStartError
from pywinauto.findbestmatch import MatchError
from pywinauto.base_wrapper import ElementNotVisible
from subprocess import Popen
from comtypes import COMError

from __init__ import BaseApp, BaseTask

def descendant(email_window, control_type, title):
        """
        Selects GUI elements in open window
        """
        descendant = email_window.descendants(control_type=control_type, title=title)
        return descendant

class Email(BaseTask):
    """
    Parent class of SendEmail and ReadEmail to combat duplicate code
    """

    def start(self):
        '''
        Uses the start method defined in BaseTask class
        '''
        super().start()

        # Get outlook application
        self.outlook_app = self.app.open()
        self.outlook = self.outlook_app.top_window()

    def stop(self):
        '''
        Uses the stop method defined in BaseTask class
        '''
        super().stop()

class SendEmail(Email):
    """
    Sends Emails

    Attributes
    ----------

    recipient_list : list
        A list of recipient names 
    cc_list : list
        A list of names that are CC'ed into the email
    subject : str
        The subject header of the email
    body : str
        The message body of the email
    attachment_list : list
        A list of attachments to send with the email


    Methods
    -------

    task_gen_info(recipient_list=[], cc_list=[], subject="", body="", attachment_list=[], random_attachment_dir="%USERPROFILE%\\Documents\\", random_attachment_count=0)
        Generates standard information in order to send the email
    main()
        Sends the email
    """

    def task_gen_info(self, recipient_list=[], cc_list=[], subject="", body="", attachment_list=[], random_attachment_dir="%USERPROFILE%\\Documents\\", random_attachment_count=0):
        """
        Generates standard information in order to send the email
        """

        self.app = self.client.modules.get_app("apps.outlook", APPS[0])(self.client) # This initalises the app we are going to open
        #self.text_generator = TextGenerator(self.client) # This initalises the text generator
        self.recipient_list = recipient_list
        self.cc_list = cc_list
        # If no subject/body is passed, use text generator
        # Generated subject and body removed, see outlook.py
        self.subject = "This is the subject of an email"
        self.body = "This is the body of an email"
        self.attachment_list = attachment_list #attachment code removed for dialedback version, see outlook.py

    async def main(self):
        """
        Sends the email
        """
        if not self.recipient_list:
        # Test Email
            self.recipient_list = ["testemail@cardiff.ac.uk"]
            new_email_button = descendant(self.outlook, "Button", "New Email" )            

        #If theres no email button an error is logged in the debugger
        if not len(new_email_button):
            self.debug_logger.warning("Failed to find new email button - attempting shortcut key")
            keyboard.send_keys("^n")

        #Else the button is clicked
        else:
            new_email_button[0].click()

        #Finds window with the title argument using regex
        email_window = self.outlook_app.window(title_re=r".* - Message \(HTML\)")

        subject_edit = descendant(email_window, "Edit", "Subject")
        subject_edit[0].set_edit_text(self.subject)

        body_edit = descendant(email_window, "Edit", "") # TODO might not need. writes body another way further down
        body_edit[0].set_edit_text(self.body)

        #Iterate through the recipient list and add each one to the "To" edit box
        for recipient in self.recipient_list: 
            recipient_edit = descendant(email_window, "Edit", "To")

            #Types recipient into the "To" edit box with spaces and a pause after each keystroke
            recipient_edit[0].type_keys(recipient + "; ", with_spaces=True, pause=0.05)

        for person in self.cc_list:
            cc_edit = descendant(email_window, "Edit", "Cc")
            cc_edit[0].type_keys(person + "; ", with_spaces=True, pause=0.05)

        #TODO ASK ANDREW (inspected on webapp, why is label body match but type is not a match)
        email_window.window(auto_id="Body").type_keys( 
            self.body,
            with_spaces=True,
            with_newlines=True,
            with_tabs=True,
            pause=0.05)
        
        #NCSC code does not use the descendants() function within the pywinauto library for "Send" button
        send_button = descendant(email_window, "Button", "Send")
        #If theres no email button an error is logged in the debugger
        if not len(send_button):
            self.debug_logger.warning("Failed to find Ssend button - attempting shortcut key")
            keyboard.send_keys("%s")

        #Else the button is clicked
        else:
            send_button[0].click()


        #Simulate a person reading through an email
        n = random.randint(0, 60)
        time.sleep(n)

class ReadEmail(Email):
    """
    Reads and Replies to emails.
    """

    def task_gen_info(self, client, reply_body):
        self.app = self.client.modules.get_app("apps.outlook", APPS[0])(self.client) # This initalises the app we are going to open
        self.text_generator = TextGenerator(self.client)
        self.reply_body = "Default" #self.text_generator.gen_paragraph()
        self.reply_chance = random.random(0, 1) # Chance that the VM will reply to email 

    def reply(self):
        """
        Reply to email
        """

        reply_button = descendant(self.outlook, "Button", "Reply")
        reply_button[0].click()

        #Reply button does not produce popup window so no need to find new window
        reply_window = self.outlook
        reply_window.type_keys(self.reply_body)
        #COMMENTED OUT CODE BELOW
        #type_keys_into_window(reply_window.window(title="Form Regions").window(auto_id="Body"), self.reply_body)

        send_button = descendant(self.outlook, "Button", "Send")
        send_button[0].click()

    def scroll(self, timeout):
        """
        Scrolls through email
        """
        try:
            message = self.outlook.window(auto_id="Body")
        except ElementNotFoundError:
            # If we can't find the element, just wait timeout
            time.sleep(timeout)
            return

        end = time.time() + timeout
        while time.time() <= end:
            random_action = random.randint(1, 15) #Reason for 15 seems unjustified
            if random_action <= 1:
                for i in range(3):
                    try:
                        message.type_keys("{DOWN}")
                    except ElementNotFoundError:
                        # If body disappears, return
                        return
            else:
                return           
            return
        
    async def main(self):
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

                    
                  
                   

                    # reply to email
                    if random.randint(0, 100) < self.reply_percentage_chance:
                        self.reply_to_email()
                

    """
    Switch in and switch out taken from NCSC code as it relates to the base task and maybe used by SUS
    -James Morton    
    """
    def switch_in(self):
        """
        Focuses on the main outlook window
        """     
        self.outlook.set_focus()

        super().switch_in()
    
    def switch_out(self):
        super().switch_out()        

class Outlook(BaseApp):
    def method():
        return
    
APPS = ["Outlook"]
TASKS = ["ReadEmail", "SendEmail"]
