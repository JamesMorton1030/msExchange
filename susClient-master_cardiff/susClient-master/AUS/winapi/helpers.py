import ctypes
import ctypes.wintypes as wintypes


from winapi.constants import (
    PHANDLE,
    INVALID_HANDLE_VALUE,
    PLUID,
    LUID,
    LPPROC_THREAD_ATTRIBUTE_LIST,
    PSIZE_T,
    DWORD_PTR,
    PVOID,
    SIZE_T,
    LPSECURITY_ATTRIBUTES,
    LPPROCESS_INFORMATION,
    PROCESS_INFORMATION,
)

# these function definitions are mostly similar to the ones from winappdbg -
# they were used as a base to build these

# https://github.com/MarioVilas/winappdbg/blob/master/winappdbg

# we can define a function to handle errors for us with ctypes,
# this is a nice simple one to raise if zero or null, to avoid repeating code


def RaiseIfFalsy(result, func=None, args=()):
    if not result:
        raise ctypes.WinError(ctypes.windll.kernel32.GetLastError())
    return result


# define our functions for use later,
# along with argument helpers

# BOOL WINAPI OpenProcessToken(
#   __in   HANDLE ProcessHandle,
#   __in   DWORD DesiredAccess,
#   __out  PHANDLE TokenHandle
# );
def OpenProcessToken(ProcessHandle, DesiredAccess):
    _OpenProcessToken = ctypes.windll.advapi32.OpenProcessToken
    _OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, PHANDLE]
    _OpenProcessToken.restype = bool
    _OpenProcessToken.errcheck = RaiseIfFalsy

    # allocate space for the new token
    NewTokenHandle = wintypes.HANDLE(INVALID_HANDLE_VALUE)

    _OpenProcessToken(ProcessHandle, DesiredAccess, ctypes.pointer(NewTokenHandle))
    return NewTokenHandle


# BOOL WINAPI LookupPrivilegeValue(
#   __in_opt  LPCTSTR lpSystemName,
#   __in      LPCTSTR lpName,
#   __out     PLUID lpLuid
# );
def LookupPrivilegeValueA(lpName, lpSystemName=None):
    _LookupPrivilegeValueA = ctypes.windll.advapi32.LookupPrivilegeValueA
    _LookupPrivilegeValueA.argtypes = [wintypes.LPSTR, wintypes.LPSTR, PLUID]
    _LookupPrivilegeValueA.restype = bool
    _LookupPrivilegeValueA.errcheck = RaiseIfFalsy

    # allocate space for the LUID struct
    lpLuid = LUID()

    _LookupPrivilegeValueA(lpSystemName, lpName, ctypes.pointer(lpLuid))
    return lpLuid


# BOOL WINAPI AdjustTokenPrivileges(
#   __in       HANDLE TokenHandle,
#   __in       BOOL DisableAllPrivileges,
#   __in_opt   PTOKEN_PRIVILEGES NewState,
#   __in       DWORD BufferLength,
#   __out_opt  PTOKEN_PRIVILEGES PreviousState,
#   __out_opt  PDWORD ReturnLength
# );
def AdjustTokenPrivileges(TokenHandle, NewState):
    _AdjustTokenPrivileges = ctypes.windll.advapi32.AdjustTokenPrivileges
    _AdjustTokenPrivileges.argtypes = [
        wintypes.HANDLE,
        wintypes.BOOL,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.LPVOID,
    ]
    _AdjustTokenPrivileges.restype = bool
    _AdjustTokenPrivileges.errcheck = RaiseIfFalsy

    _AdjustTokenPrivileges(
        TokenHandle,
        False,
        ctypes.pointer(NewState),
        ctypes.sizeof(NewState),
        None,
        None,
    )


# BOOL WINAPI CloseHandle(
#   __in  HANDLE hObject
# );
def CloseHandle(hHandle):
    _CloseHandle = ctypes.windll.kernel32.CloseHandle
    _CloseHandle.argtypes = [wintypes.HANDLE]
    _CloseHandle.restype = bool
    _CloseHandle.errcheck = RaiseIfFalsy

    _CloseHandle(hHandle)


# HANDLE WINAPI OpenProcess(
#   __in  DWORD dwDesiredAccess,
#   __in  BOOL bInheritHandle,
#   __in  DWORD dwProcessId
# );
def OpenProcess(dwDesiredAccess, bInheritHandle, dwProcessId):
    _OpenProcess = ctypes.windll.kernel32.OpenProcess
    _OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    _OpenProcess.restype = wintypes.HANDLE

    hProcess = _OpenProcess(dwDesiredAccess, bInheritHandle, dwProcessId)
    if hProcess is None:
        raise ctypes.WinError(ctypes.windll.kernel32.GetLastError())
    # RaiseIfFalsy can handle this one too, right?

    return hProcess


# BOOL WINAPI InitializeProcThreadAttributeList(
#   __out_opt   LPPROC_THREAD_ATTRIBUTE_LIST lpAttributeList,
#   __in        DWORD dwAttributeCount,
#   __reserved  DWORD dwFlags,
#   __inout     PSIZE_T lpSize
# );
def InitializeProcThreadAttributeList(dwAttributeCount):
    _InitializeProcThreadAttributeList = (
        ctypes.windll.kernel32.InitializeProcThreadAttributeList
    )
    _InitializeProcThreadAttributeList.argtypes = [
        LPPROC_THREAD_ATTRIBUTE_LIST,
        wintypes.DWORD,
        wintypes.DWORD,
        PSIZE_T,
    ]
    _InitializeProcThreadAttributeList.restype = bool

    lpSize = ctypes.c_size_t(0)  # allocate space for the size

    _InitializeProcThreadAttributeList(
        None, dwAttributeCount, 0, ctypes.pointer(lpSize)
    )

    # we don't check res here, because it is always 0 - an error - because
    # Note:  This initial call will return an error by design. This is expected behavior.
    # https://docs.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-initializeprocthreadattributelist

    RaiseIfFalsy(lpSize.value)

    # processheap = ctypes.windll.kernel32.GetProcessHeap()

    # DECLSPEC_ALLOCATOR LPVOID HeapAlloc(
    #  HANDLE hHeap,
    #  DWORD  dwFlags,
    #  SIZE_T dwBytes
    # );
    # AttributeBuffer = ctypes.windll.kernel32.HeapAlloc(processheap, 0, putithere)

    # TODO why does the above code (without doing ctypes.pointer(AttributeBuffer) at the bottom give an access violation on the HeapAlloc?
    # the only thing I didn't do was cast it to the right type, but it shouldn't matter, since one is the same as the other...

    AttributeBuffer = (wintypes.BYTE * lpSize.value)()
    _InitializeProcThreadAttributeList(AttributeBuffer, 1, 0, ctypes.pointer(lpSize))

    return AttributeBuffer


# BOOL WINAPI UpdateProcThreadAttribute(
#   __inout    LPPROC_THREAD_ATTRIBUTE_LIST lpAttributeList,
#   __in       DWORD dwFlags,
#   __in       DWORD_PTR Attribute,
#   __in       PVOID lpValue,
#   __in       SIZE_T cbSize,
#   __out_opt  PVOID lpPreviousValue,
#   __in_opt   PSIZE_T lpReturnSize
# );
def UpdateProcThreadAttribute(lpAttributeList, Attribute, Value):
    _UpdateProcThreadAttribute = ctypes.windll.kernel32.UpdateProcThreadAttribute
    _UpdateProcThreadAttribute.argtypes = [
        LPPROC_THREAD_ATTRIBUTE_LIST,
        wintypes.DWORD,
        DWORD_PTR,
        PVOID,
        SIZE_T,
        PVOID,
        PSIZE_T,
    ]
    _UpdateProcThreadAttribute.restype = bool
    _UpdateProcThreadAttribute.errcheck = RaiseIfFalsy

    _UpdateProcThreadAttribute(
        ctypes.pointer(lpAttributeList),
        0,
        Attribute,
        ctypes.pointer(Value),
        ctypes.sizeof(Value),
        None,
        None,
    )


# VOID WINAPI DeleteProcThreadAttributeList(
#   __inout  LPPROC_THREAD_ATTRIBUTE_LIST lpAttributeList
# );
def DeleteProcThreadAttributeList(lpAttributeList):
    _DeleteProcThreadAttributeList = (
        ctypes.windll.kernel32.DeleteProcThreadAttributeList
    )
    # _DeleteProcThreadAttributeList.argtypes = [LPPROC_THREAD_ATTRIBUTE_LIST]
    _DeleteProcThreadAttributeList.restype = None
    # no error check - it returns nothing

    _DeleteProcThreadAttributeList(ctypes.pointer(lpAttributeList))


# BOOL WINAPI CreateProcess(
#   __in_opt     LPCTSTR lpApplicationName,
#   __inout_opt  LPTSTR lpCommandLine,
#   __in_opt     LPSECURITY_ATTRIBUTES lpProcessAttributes,
#   __in_opt     LPSECURITY_ATTRIBUTES lpThreadAttributes,
#   __in         BOOL bInheritHandles,
#   __in         DWORD dwCreationFlags,
#   __in_opt     LPVOID lpEnvironment,
#   __in_opt     LPCTSTR lpCurrentDirectory,
#   __in         LPSTARTUPINFO lpStartupInfo,
#   __out        LPPROCESS_INFORMATION lpProcessInformation
# );
def CreateProcessA(
    lpApplicationName,
    lpCommandLine,
    lpProcessAttributes,
    lpThreadAttributes,
    bInheritHandles,
    dwCreationFlags,
    lpEnvironment,
    lpCurrentDirectory,
    lpStartupInfo,
):
    _CreateProcessA = ctypes.windll.kernel32.CreateProcessA
    _CreateProcessA.argtypes = [
        wintypes.LPSTR,
        wintypes.LPSTR,
        LPSECURITY_ATTRIBUTES,
        LPSECURITY_ATTRIBUTES,
        wintypes.BOOL,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.LPSTR,
        wintypes.LPVOID,
        LPPROCESS_INFORMATION,
    ]
    _CreateProcessA.restype = bool
    _CreateProcessA.errcheck = RaiseIfFalsy

    lpCommandLine = ctypes.create_string_buffer(
        lpCommandLine, max(259, len(lpCommandLine) + 1)
    )
    # for safety, this creates the string buffer with the maximum length of 259 and returns the c_char_p

    # set up PROCESS_INFORMATION -
    # this is where the process information will be stored once the process has been started

    lpProcessInformation = PROCESS_INFORMATION()

    lpProcessInformation.hProcess = INVALID_HANDLE_VALUE
    lpProcessInformation.hThread = INVALID_HANDLE_VALUE
    lpProcessInformation.dwProcessId = 0
    lpProcessInformation.dwThreadId = 0
    # nothing yet

    _CreateProcessA(
        lpApplicationName,
        lpCommandLine,
        lpProcessAttributes,
        lpThreadAttributes,
        bInheritHandles,
        dwCreationFlags,
        lpEnvironment,
        lpCurrentDirectory,
        ctypes.pointer(lpStartupInfo),
        ctypes.pointer(lpProcessInformation),
    )
    return lpProcessInformation


# https://docs.microsoft.com/en-us/windows/win32/api/psapi/nf-psapi-enumprocesses
def EnumProcesses():

    _EnumProcesses = ctypes.windll.psapi.EnumProcesses
    _EnumProcesses.restype = bool
    _EnumProcesses.argtypes = [wintypes.LPVOID, wintypes.DWORD, wintypes.LPDWORD]
    _EnumProcesses.errcheck = RaiseIfFalsy

    sizeattempt = 64
    # we cannot predict how many processes there will be -
    # so we make an array of this size,

    while True:
        ProcessIDArray = (wintypes.DWORD * sizeattempt)()
        ArraySize = ctypes.sizeof(ProcessIDArray)
        ReturnedArraySize = wintypes.DWORD()  # allocate space

        _EnumProcesses(
            ctypes.pointer(ProcessIDArray), ArraySize, ctypes.pointer(ReturnedArraySize)
        )

        if ReturnedArraySize.value < ArraySize:
            break
        else:
            sizeattempt = sizeattempt * 2

        # if the size of the returned array equals our size attempt,
        # we assume that there were more processes for us to enumerate,
        # so try again, doubling the size attempt
        # (note that there is 1 case where this isn't true, if guessed the process number exactly,
        # but without running again with a larger process number we have no way of telling if we did or not)

    # return the array and the number of items in the array
    return ProcessIDArray, ReturnedArraySize.value // ctypes.sizeof(wintypes.DWORD)


# https://docs.microsoft.com/en-us/windows/win32/api/psapi/nf-psapi-getmodulebasenamea
# or
# https://docs.microsoft.com/en-us/windows/win32/api/psapi/nf-psapi-getprocessimagefilenamea

# I think we need GetProcessImageFilename,
# because the other one requires it to be owned by the process running it


def GetProcessImageFileName(hProcess):

    _GetProcessImageFileNameA = ctypes.windll.psapi.GetProcessImageFileNameA
    _GetProcessImageFileNameA.argtypes = [
        wintypes.HANDLE,
        wintypes.LPSTR,
        wintypes.DWORD,
    ]
    _GetProcessImageFileNameA.restype = wintypes.DWORD
    _GetProcessImageFileNameA.errcheck = RaiseIfFalsy

    max_filename_size = 256
    # again, similar to EnumProcesses, guess at the maximum size

    while True:
        lpFilename = ctypes.create_string_buffer(b"", max_filename_size)
        # create the buffer for the filename to go into

        bytes_written = _GetProcessImageFileNameA(
            hProcess, lpFilename, max_filename_size
        )

        if bytes_written < max_filename_size - 1:
            break
        else:
            max_filename_size = max_filename_size * 2
        # and again, if we've filled up our entire filename buffer, assume there's more filename to follow
        # so increase the max filename size and retry

    # return the actual filename
    return lpFilename.value


# choose parent for a windows process -
# based on https://blog.didierstevens.com/2009/11/22/quickpost-selectmyparent-or-playing-with-the-windows-process-tree/
# and the implementation in python,
# https://github.com/MarioVilas/winappdbg/blob/master/tools/SelectMyParent.py

