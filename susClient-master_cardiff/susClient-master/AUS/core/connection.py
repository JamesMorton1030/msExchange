from requests import Session
from requests.exceptions import ConnectionError
from urllib.parse import urljoin

class Connection(Session):
    """A connection object which wraps a requests session so that the
    servers address is entered in front of every URL.
    """

    def __init__(self, api_url):
        self.api_url = api_url

        super().__init__()

    def request(self, method, endpoint, **kwargs):
        """Automatically prepends the servers information to the start
        of any request. Connection errors are handled and will return
        None if one is raised.
        """
        url = urljoin(self.api_url, endpoint)
        try:
            response = super().request(method, url, **kwargs)
            
            return response
        except ConnectionError:
            print("Failed to connect to the URL: " + url)
            return None