"""The utilities package contains common functionality which can be
used throughout the simulator. All utilities are designed so that they
are stateless which ensures compatability throughout the client.
"""

from datetime import datetime
from json import load
from random import randrange

def load_json(file_name, default=None):
    """This function will open a JSON file and return the contents. If
    there are any problems opening the file *default* is returned.
    """
    try:
        with open(file_name, "r") as file:
            return load(file)
    except FileNotFoundError:
        return default


def select_random(array, total=100):
    """Accepts a two dimensional array of format ``[chance, value]``
    and selects a random item from the array based on the chance.
    """
    selected = randrange(0, total)
    lower = 0
    for item in array:
        if lower <= selected < lower + item[0]:
            return item[1]
        lower += item[0]
    raise ValueError("Random array invalid")


def str_to_time(time_string):
    """Converts a string representing a time into a datetime object for
    use by other parts of the client.
    """
    parts = time_string.split(":")
    parts = [int(i) for i in parts]
    now = datetime.now()
    if len(parts) == 2:
        time = now.replace(hour=parts[0], minute=parts[1])
    else:
        time = now.replace(hour=parts[0], minute=parts[1], second=parts[2])
    return time.timestamp()
