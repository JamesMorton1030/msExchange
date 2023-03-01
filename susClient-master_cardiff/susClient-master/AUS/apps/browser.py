"""Browser
"""

import random
import time
import sys
import os

from msedge.selenium_tools import Edge, EdgeOptions
from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import InvalidArgumentException
from selenium.common.exceptions import UnexpectedAlertPresentException
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions

from apps import BaseApp, BaseTask
from utils import link_check

class BrowseWebsite(BaseTask):
    """Browses the internet"""

    def task_load(self, max_depth=10, url_list=[], max_urls=30, use_browser="Chrome", add_url_to_command_line=False):
        """Retrieves a reference to which app to use
        and initialises default variables
        """
        # Sanitise browser input. Possible choices are Edge, Chrome, Firefox and Random
        if use_browser == "Random": 
            use_browser = random.choice(APPS)

        if use_browser not in APPS:
            use_browser = "Chrome"

        # Also check operating system (Edge is not yet supported on Linux)
        if sys.platform == "linux" and use_browser == "Edge":
            self.debug_logger.warning("BrowseWebsites attempted to use Edge on Linux, defaulting browser to Chrome")
            use_browser = "Chrome"

        self.app = self.client.modules.get_app("apps.browser", use_browser)(self.client)
        self.use_browser = use_browser
        self.url_list = url_list
        self.max_depth = max_depth
        self.add_url_to_command_line = add_url_to_command_line
        self.first_url = None

        # Check whether url_list is [], if so, request a new list of urls
        if not self.url_list:
            response = self.client.connection.post("/api/resources/browsing", json={
                    "url_count": max_urls,
                    "url_tags": {"countries": {"$in": ["any", "uk"]}} # TODO: Insert profile logic
                }
            )

            if response is not None and response.status_code == 200:
                # Update url list
                self.url_list = response.json()
            else:
                # Something went wrong getting a url list, just use a few default URLs
                self.debug_logger.warning("Failed to retrieve URLs from API, status code {status_code}", status_code=response.status_code if response else "N/A")
            
            # Double check that we have some URLs
            if not self.url_list:
                self.url_list = ["https://stackoverflow.com",
                                "https://bbc.co.uk",
                                "https://reddit.com"]

    def start(self):
        """Starts browser application"""
        # As per schema, call super().start() at the start of the task
        super().start()
        
        if self.add_url_to_command_line:
            # Pick a random url to use as our first URL
            self.first_url = random.choice(self.url_list)

        # Start the webdriver
        self.driver = self.app.open(self.first_url)

        self.activity_logger.info("Using browser {browser} to browse websites", state="RUNNING", browser=self.use_browser)

        if self.add_url_to_command_line:
            self.activity_logger.info("Started browser with URL \"{page_url}\" in command line arguments", state="RUNNING", page_url=self.first_url)

    def stop(self):
        """Ends the browser"""
        # As per schema, call super().stop() at the end of the task
        super().stop()

    def get_page_link(self):
        """Gets all links on the current page and finds one that can be navigated to"""
        
        current_url = "UNKNOWN"

        try: 
            current_url = str(self.driver.current_url) 
        except TimeoutException:
            self.debug_logger.warning("Failed to retrieve current URL of browser, using \"UNKNOWN\"")

        # Find all 'a' tags on current webpage
        try:
            links = self.driver.find_elements_by_tag_name("a")
        except TimeoutException:
            self.debug_logger.warning("Attempted to find a tags on {current_url}, but received TimeoutException", current_url=current_url)
            return None
            
        # Shuffle the links, so we don't always click on the first one
        random.shuffle(links)

        # Preprocess each a tag to get the actual link and add to a list
        for link in links:
            # Get link pointed to by a tag
            try:
                attr = link.get_attribute("href")
            except StaleElementReferenceException:
                # If the element doesn't exist anymore, just skip to the next link
                continue

            if link_check.is_link(str(attr)) is not None:
                return str(attr)

        # Otherwise, if we go through every single link and they're invalid (unlikely)
        # return None
        self.debug_logger.info(f"Found no links to navigate to on {current_url}", current_url=current_url)
        return None

    def random_scroll(self, timeout=None, speed=3, down=3, up=1, wait=2):
        """Random scrolling on webpages"""
        start = time.time()

        if timeout is None:
            #timeout set to a random time betweem 10 sec and 20 sec
            timeout = random.randint(10, 20)
        end = start + timeout

       # Get the body of the web page, while waiting for page to load
        exceptions = (NoSuchElementException, StaleElementReferenceException, UnexpectedAlertPresentException)
        try:
            web_page = WebDriverWait(self.driver, 10, ignored_exceptions=exceptions)\
                                    .until(lambda driver: driver.find_element_by_tag_name("body"))
        except TimeoutException:
            return

        try:
            # while there is still time left
            while time.time() <= end:
                total = down + up + wait
                random_action = random.randint(1, total)

                if random_action <= down:
                    for _ in range(5):
                        # Scroll down
                        web_page.send_keys(Keys.DOWN)
                elif down < random_action <= (down + up):
                    for _ in range(5):
                        # Scroll up
                        web_page.send_keys(Keys.UP)
                else:
                    # Wait...
                    time.sleep(wait)
        except StaleElementReferenceException:
            pass

        time.sleep(speed)

    async def main(self):
        """Main browsing function"""
        first_run = True

        # Keep going to new links while the timer is still running
        while not self.timer:
            # We've just navigated to a new link, reset the depth
            depth = 0

            # If we're on the first iteration of the loop, and add_url_to_command_line is True
            # set page_url to self.first_url (which is the url appended to the command line)
            if first_run and self.first_url:
                page_url = self.first_url
            else:
                page_url = random.choice(self.url_list)
                self.activity_logger.info("Navigating to page picked from url_list from the task option", state="RUNNING", page_url=page_url)

            first_run = False

            # While our depth hasn't reach max depth, keep finding a link we can navigate to on this page
            # At maximum depth, we just always navigate away
            while depth <= self.max_depth:
                # Navigate to the page and scroll down
                print(f"Navigating to page: {page_url}")
                # Force the webdriver to recieve the url as a string
                try:
                    # If this is the first run and we have a first_url, we don't need to get() as we're already on this page
                    if not (first_run and self.first_url):
                        self.driver.get(page_url)
                except InvalidArgumentException:
                    # This happens at some weird links, if it does happen, we can just stay on the same page and carry on, doesn't matter too much
                    self.debug_logger.warning("InvalidArgumentException occured on page url {page_url}", state="RUNNING", page_url=page_url) 
                except WebDriverException:
                    # This happens on urls such as: about:neterror?e=dnsNotFound&u=...
                    self.debug_logger.warning("WebDriverException occured on page url {page_url}", state="RUNNING", page_url=page_url) 

                self.random_scroll()
                depth += 1

                # However, the deeper we get down depth, the more chance we should just navigate to a different url
                # So the chance of navigating to a url in our url_list should increase after each increase in depth
                number = random.randint(depth, self.max_depth)

                if number == self.max_depth:
                    # Navigate away prematurely
                    break
                else:
                    # Otherwise find a new page link
                    page_url = self.get_page_link()

                    # If no valid link is found, just navigate away prematurely
                    if page_url is None:
                        break
                    else:
                        # Valid link is found, note that we're going to a link we found on the page
                        self.activity_logger.info("Navigating to link found from a hyperlink on the page", state="RUNNING", page_url=page_url)



class Browser(BaseApp):
    """Application for web browsing."""

    # Use edge by default
    DRIVER = webdriver.Edge

    def open(self, first_url):
        self.webdriver = None
        self.webdriver_options = None

        """Start the default browser"""
        if not self.client.app_manager.is_open(self.__class__.__name__):
            # The browser is not open, open it
            # Note that our first_url should be added to the command line arguments if not None
            # NOTE: On Chromium based browsers, we have to add an additional parameter --sus-ignore-me
            # otherwise, attempting to add just the URL will result in chromedriver adding -- to the start of the URL, rendering it useless
            # Please see https://github.com/jellyfishResearch/susClient/issues/13
            self.webdriver_options = self.get_options(first_url)
            self.webdriver = self.DRIVER(options=self.webdriver_options)

            # add it to app_manager
            self.client.app_manager.add(self.__class__.__name__, self.webdriver)
        else:
            # browser window exists, therefore get the object
            self.webdriver = self.client.app_manager.get(self.__class__.__name__)
        return self.webdriver

    def close(self):
        if self.webdriver:
            self.webdriver.quit()
            self.webdriver.stop_client()
            self.webdriver = None
        
        self.client.app_manager.remove(self.__class__.__name__)
        return True


    def send_keys(self, place, text, delay=0.08):
        """Types into a box with delay between keys"""
        for char in text:
            place.send_keys(char)
            time.sleep(delay)

class Edge(Browser):
    """Extension of Browser class for Edge"""
    # Note that we are using msedge.selenium_tools's Edge
    DRIVER = Edge

    def get_options(self, first_url):
        # Return an instance of EdgeOptions, and if first_url is not None,
        # append that argument to EdgeOptions
        options = EdgeOptions()
        # Use chromium edge, instead of legacy edge
        options.use_chromium = True
        if first_url:
            options.add_argument("--sus-ignore-me {}".format(first_url))

        return options

class Chrome(Browser):
    """Extension of Browser class for Chrome"""
    DRIVER = webdriver.Chrome

    def get_options(self, first_url):
        # Return an instance of ChromeOptions, and if first_url is not None,
        # append that argument to ChromeOptions
        options = webdriver.ChromeOptions()
        if first_url:
            options.add_argument("--sus-ignore-me {}".format(first_url))

        return options

class Firefox(Browser):
    """Extension of Browser class for Firefox"""
    DRIVER = webdriver.Firefox

    def get_options(self, first_url):
        # Return an instance of FirefoxOptions, and if first_url is not None,
        # append that argument to FirefoxOptions
        options = webdriver.FirefoxOptions()
        if first_url:
            options.add_argument(first_url)

        return options

APPS = ["Edge", "Chrome", "Firefox"]
TASKS = ["BrowseWebsite"]