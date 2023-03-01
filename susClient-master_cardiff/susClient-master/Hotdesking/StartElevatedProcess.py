import pywintypes
import win32api
import win32security
import win32con
import win32process
import ctypes
import psutil


def find_process_id(process_name):
    
    #loop through all the processes until we find winlogon
    for process in psutil.process_iter():
        if process_name in process.name():
            return process.pid

    #this shouldn't possible but we will return 0 anyway
    return 0


def get_process_handle(process_id):
    handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, True, process_id)
    return handle


def get_process_token(process_handle):
   
    token_handle = win32security.OpenProcessToken(
        process_handle, 
        win32security.TOKEN_QUERY | win32security.TOKEN_IMPERSONATE | win32security.TOKEN_DUPLICATE
        )

    return token_handle


def duplicate_and_escalate_token(process_token):

    # make a copy of the token that is a primary token
    new_token = win32security.DuplicateTokenEx(
        process_token, win32security.SecurityIdentification,
        win32con.MAXIMUM_ALLOWED, win32security.TokenPrimary, None
        )

    # return the id of the SE_DEBUG_NAME privilege
    luid = win32security.LookupPrivilegeValue(None, win32security.SE_DEBUG_NAME)

    # enable the SE_DEBUG_NAME privilege on our duplicate token
    token_privileges = [(luid, win32security.SE_PRIVILEGE_ENABLED)]
    win32security.AdjustTokenPrivileges(new_token, False, token_privileges)

    return new_token


def create_new_process(token_handle, program, args, cwd=None):
    
    # Specify the Desktop to start the process in as the desktop used by winlogon
    startup = win32process.STARTUPINFO()
    startup.lpDesktop = R"Winsta0\Winlogon"

    win32process.CreateProcessAsUser(
        token_handle, program, args, None, None, False,
        win32process.CREATE_NEW_CONSOLE | win32con.NORMAL_PRIORITY_CLASS,
        None, cwd, startup
        )