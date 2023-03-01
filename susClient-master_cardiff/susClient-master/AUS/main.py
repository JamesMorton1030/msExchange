import os
import sys

from core.client import Client
from utils import load_json

def main():
    config = load_json("config/general.json")

    client = Client(config)
    # Verify that the client is ready to be started
    if not client.ready:
        client.logger.critical("Failed to initialise client correctly, exiting...", state="START")
        return

    client.run()


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))
    main()
