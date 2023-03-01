import ctypes
import ctypes.wintypes as wintypes
import os

from winapi.constants import (
    TOKEN_ADJUST_PRIVILEGES,
    SE_DEBUG_NAME,
    LUID_AND_ATTRIBUTES,
    SE_PRIVILEGE_ENABLED,
    TOKEN_PRIVILEGES,
    PROCESS_ALL_ACCESS,
    PROC_THREAD_ATTRIBUTE_PARENT_PROCESS,
    EXTENDED_STARTUP_INFO_PRESENT,
    STARTUPINFOEX,
    PROCESS_QUERY_INFORMATION,
)
from winapi.helpers import (
    OpenProcessToken,
    LookupPrivilegeValueA,
    AdjustTokenPrivileges,
    CloseHandle,
    OpenProcess,
    InitializeProcThreadAttributeList,
    UpdateProcThreadAttribute,
    CreateProcessA,
    DeleteProcThreadAttributeList,
    GetProcessImageFileName,
    EnumProcesses,
)


def get_pid(filename):
    """
    find the ID of a process given its filename - 
    this is used mainly to find the PID of explorer.exe
    so we can spawn apps as though they were spawned from the GUI, rather than our python script
    """

    # assisted by similar functionality in winappdbg -
    # https://github.com/MarioVilas/winappdbg

    process_array, process_array_size = EnumProcesses()
    # get a list of all the processes

    for i in range(process_array_size):
        process_id = process_array[i]

        # here we only need the rights to query information from the process,
        try:
            process_handle = OpenProcess(PROCESS_QUERY_INFORMATION, 0, process_id)

            full_process_filename = GetProcessImageFileName(process_handle)
            # print(full_process_filename, os.path.basename(full_process_filename))

            if os.path.basename(full_process_filename).decode() == filename:
                return process_id
            # TODO what to do about multiple copies of processes?
            # explorer.exe CAN exist more than once with multiple GUI windows,
            # but we should only have one main GUI, right?

            CloseHandle(process_handle)  # clean up

        except OSError:
            pass  # some processes we may not be allowed to view, skip them

    # if you couldn't find it, return error
    return -1


def escalate_privileges():
    """
    raise privileges of current process to debug,
    to allow us to interact with SYSTEM or other protected processes - 
    """

    hToken = OpenProcessToken(
        ctypes.windll.kernel32.GetCurrentProcess(), TOKEN_ADJUST_PRIVILEGES
    )

    # print(hToken.value)
    # we can pass the pointer again here, we don't need to use the value

    # we have SeDebugPrivilege: ENABLED
    # which is True, 1

    luid = LookupPrivilegeValueA(SE_DEBUG_NAME)

    attr_struct = LUID_AND_ATTRIBUTES(luid, SE_PRIVILEGE_ENABLED)
    token_struct = TOKEN_PRIVILEGES(1, attr_struct)

    AdjustTokenPrivileges(hToken, token_struct)

    # clean up
    CloseHandle(hToken)


def spawn_process(commandline, parent_id):

    """
    spawns a process with the a set parentid, using the commandline specified
    """

    # first, get handle to the parent process - we need process_create_process level privileges,
    # if we want to set it as our parent
    # https://docs.microsoft.com/en-us/windows/win32/procthread/process-security-and-access-rights

    # which is 0x0080 -
    # however, this doesn't consistenly work,
    # so to be safe ask for all available rights instead -
    # this is PROCESS_ALL_ACCESS

    ParentHandle = OpenProcess(PROCESS_ALL_ACCESS, 0, parent_id)

    ParentHandleCast = ctypes.c_void_p(ParentHandle)
    # cast it first, so we can make a pointer to it

    # now we need to make our attribute list,

    # initialize an attribute list with space for 1 -
    AttributeBuffer = InitializeProcThreadAttributeList(1)

    # update it with the only attribute that we have -
    # (0x00020000,ParentHandleCast)
    # 0x00020000 = PROC_THREAD_ATTRIBUTE_PARENT_PROCESS -
    # since that's what we're saying the ParentHandle is this processes Parent Process

    UpdateProcThreadAttribute(
        AttributeBuffer, PROC_THREAD_ATTRIBUTE_PARENT_PROCESS, ParentHandleCast
    )

    AttributeList = ctypes.cast(ctypes.pointer(AttributeBuffer), ctypes.c_void_p)

    # for our purposes, lpapplicationname is always None,
    # because lpCommandLine can be used to achieve the exact same thing -
    # lpApplicationName is an inferior version, as it requires the full path to anything as well

    # lpCommandLine = b"notepad"

    lpProcessAttributes = None
    lpThreadAttributes = None
    bInheritHandles = True

    dwCreationFlags = EXTENDED_STARTUP_INFO_PRESENT

    lpEnvironment = None
    lpCurrentDirectory = None

    StartupInfoEx = STARTUPINFOEX()
    StartupInfo = StartupInfoEx.StartupInfo

    StartupInfo.cb = ctypes.sizeof(STARTUPINFOEX)
    StartupInfo.lpReserved = 0
    StartupInfo.lpDesktop = 0
    StartupInfo.lpTitle = 0
    StartupInfo.dwFlags = 0
    StartupInfo.cbReserved2 = 0
    StartupInfo.lpReserved2 = None

    StartupInfoEx.lpAttributeList = AttributeList
    lpStartupInfo = StartupInfoEx

    # finally, we're free - we can do it

    newprocess = CreateProcessA(
        None,
        commandline.encode(),
        lpProcessAttributes,
        lpThreadAttributes,
        bInheritHandles,
        dwCreationFlags,
        lpEnvironment,
        lpCurrentDirectory,
        lpStartupInfo,
    )

    # CreateProcessW takes Unicode,
    # CreateProcessA takes ANSI string - we want A

    # clean up

    DeleteProcThreadAttributeList(AttributeBuffer)
    CloseHandle(ParentHandle)

    return newprocess.dwProcessId


# choose parent for a windows process -
# based on https://blog.didierstevens.com/2009/11/22/quickpost-selectmyparent-or-playing-with-the-windows-process-tree/
# and the implementation in python,
# https://github.com/MarioVilas/winappdbg/blob/master/tools/SelectMyParent.py
