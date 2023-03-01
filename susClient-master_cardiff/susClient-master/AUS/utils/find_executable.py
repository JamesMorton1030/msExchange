import os
import locale
import struct

def get_executable_path(program_name, match_exact=False, match_case=False):
    """
    This method will find the executable path of a program. It searches the Start Menu folder and
    attempts to match the shortcut names to the program_name passed. 
    
    If match_exact is true, the shortcut name must match program_name otherwise the method 
    checks whether program_name is a substring of the shortcut name.

    If match_case is true, the name comparison will be case sensitive otherwise it will not be.

    The target of the matched shortcut is returned, or None if no shortcut is found.
    """
    # TODO: Should this instead be done at the start of the client and the list of executables stored for quick access?
    # List of the folders that shortcuts will be searched for
    search_folders = [r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs"]
    
    if not match_case:
        program_name = program_name.lower()
        
    for folder in search_folders:
        # Get a list of the files inside the folder
        for file in os.listdir(folder):
            # Check it's a shortcut
            if file.endswith(".lnk"):
                shortcut_name = file.replace(".lnk", "")
                
                # If match_case is false, lower the name
                if not match_case:
                    shortcut_name = shortcut_name.lower()

                # Check whether it satisfies our program name
                if (match_exact and shortcut_name == program_name) or (program_name in shortcut_name and not match_exact):
                    # Read the shortcut target and return it
                    return read_shortcut_target(os.path.join(folder, file))
    
    # No shortcuts satisified our conditions, return None
    return None


# https://gist.github.com/Winand/997ed38269e899eb561991a0c663fa49
# Function to read the target of the shortcut
def read_shortcut_target(path):
    # http://stackoverflow.com/a/28952464/1119602
    with open(path, 'rb') as stream:
        content = stream.read()
        # skip first 20 bytes (HeaderSize and LinkCLSID)
        # read the LinkFlags structure (4 bytes)
        lflags = struct.unpack('I', content[0x14:0x18])[0]
        position = 0x18
        # if the HasLinkTargetIDList bit is set then skip the stored IDList 
        # structure and header
        if (lflags & 0x01) == 1:
            position = struct.unpack('H', content[0x4C:0x4E])[0] + 0x4E
        last_pos = position
        position += 0x04
        # get how long the file information is (LinkInfoSize)
        length = struct.unpack('I', content[last_pos:position])[0]
        # skip 12 bytes (LinkInfoHeaderSize, LinkInfoFlags and VolumeIDOffset)
        position += 0x0C
        # go to the LocalBasePath position
        lbpos = struct.unpack('I', content[position:position+0x04])[0]
        position = last_pos + lbpos
        # read the string at the given position of the determined length
        size = (length + last_pos) - position - 0x02
        content = content[position:position+size].split(b'\x00', 1)
        return content[-1].decode('utf-16' if len(content) > 1
                                  else locale.getdefaultlocale()[1])