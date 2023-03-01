"""
SUS use of Exchange Server,
Outlook
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
    """
    Sends Emails
    """
    def task_gen_info(self, recipient_list=[], cc_list=[], subject="", body="", attachment_list=[], random_attachment_dir="%USERPROFILE%\\Documents\\", random_attachment_count=0):
        """
        Generates standard information in order to send the email.
        """

        self.app = self.client.modules.get_app("apps.outlook", APPS[0])(self.client)
        self.text_generator = TextGenerator(self.client)
        self.recipient_list = recipient_list
        self.cc_list = cc_list
        # If no subject/body is passed, use text generator
        self.subject = subject if subject else self.text_generator.gen_sentence()
        self.body = body.replace("\\n", "\n") if body else self.text_generator.gen_paragraph()
        self.attachment_list = attachment_list





APPS = ["Outlook"]
TASKS = ["ReadEmail", "SendEmail"]
