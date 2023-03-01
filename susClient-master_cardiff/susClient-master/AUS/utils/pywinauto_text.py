import time
import random
from pywinauto.base_wrapper import ElementNotVisible
from pywinauto.application import WindowSpecification

# This horrendous array contains keys that might accidentally get pressed
# For example, the keys next to q (a and w) might get pressed, if this happens, press backspace and retype the correct key
MISTYPED_KEYS = { "q": "aw", "w": "qse", "e": "wdr", "r": "eft", "t": "rgy", "y": "thu", "u": "yji", "i": "uko", "o": "ilp", "p": "o;[", "a": "qsz", "s": "awdzx", "d": "efcxs", "f": "drcvg", "g": "fthvb", "h": "gybnj", "j": "hnmku", "k": "jiml", "l": "k;o.", "z": "xsa", "x": "zsdc", "c": "xdfv", "v": "cfgb", "b": "vghn", "n": "bhjm", "m": "njk" }  

def type_keys_into_window(window, text, typing_delay=0.08, line_delay=0.1, enable_mistypes=True):
    """This function types text into a PyWinAuto window. Characters will
    be sanitised before being enterer. If enable_mistypes is true, some
    characters will be mistyped then backspaced and entered correctly.

    If an ElementNotVisible error is caught, the text that has not yet been written will be returned.
    This allows the caller to handle this error (i.e. for Word, update the window that is being written to)
    and then recall this function to finish the typing.
    """
    # Making the window wait to exist causes the windowspecification to resolve
    # This means that every time we try typing to it, it doesn't attempt to resolve
    # Resolving is incredibly slow so by doing this, we store the single resolution result
    if isinstance(window, WindowSpecification):
        window = window.wait("exists")

    for char_index, character in enumerate(text):
        # Sometimes (10% chance), the user will type the wrong key, so we'll type the wrong character, backspace and then the correct character
        # TODO: Maybe add in extra delay if they type something in wrong
        typed_characters = sanitise_key(character)
        if character in MISTYPED_KEYS and random.random() < 0.1:
            typed_characters = sanitise_key(random.choice(MISTYPED_KEYS[character])) + "{BACKSPACE}" + sanitise_key(character)
        
        try:
            window.type_keys(typed_characters, with_spaces=True, with_tabs=True, with_newlines=True, pause=typing_delay)
        except (ElementNotVisible, RuntimeError):
            # Element is no longer on screen, return what text has not been entered
            return text[char_index:]

        if character == "\n":
            # Wait after the line has been typed, imitiating "thinking"
            time.sleep(line_delay)
    
    # Just to be safe, return None
    return None

def sanitise_key(key):
    """This function will sanitise a character before it is passed into pywinauto's send_keys
    as some keys are reserved. For example, "{" and "}". For characters with no special purpose, this
    function will just return the character.
    """
    # https://pywinauto.readthedocs.io/en/latest/code/pywinauto.keyboard.html
    # Use curly brackers to escape modifiers and type reserved symbols as single keys
    # This function will return {{{}}}
    return "{{{}}}".format(key) if key in ["{", "}", "+", "^", "%", "(", ")", "~"] else key