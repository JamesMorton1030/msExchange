import ctypes
import ctypes.wintypes as wintypes


# PROCESS_ALL_ACCESS is a macro - we can calculate our value via
PROCESS_ALL_ACCESS = 0x000F0000 | 0x00100000 | 0xFFF
# 0x001F0FFF

PROCESS_QUERY_INFORMATION = 0x00000400
# https://docs.microsoft.com/en-us/windows/win32/procthread/process-security-and-access-rights

EXTENDED_STARTUP_INFO_PRESENT = 0x00080000
# https://docs.microsoft.com/en-gb/windows/win32/procthread/process-creation-flags

PROC_THREAD_ATTRIBUTE_PARENT_PROCESS = 0x00020000

INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

# if ctypes.sizeof(ctypes.c_void_p) == 4:
# 	INVALID_HANDLE_VALUE = 0xFFFFFFFF
# elif ctypes.sizeof(ctypes.c_void_p) == 8:
# 	INVALID_HANDLE_VALUE = 0xFFFFFFFFFFFFFFFF

# 32 bit vs 64 bit -
# it's -1 as a void pointer, so it depends on the arch


TOKEN_ADJUST_PRIVILEGES = 0x00000020

SE_DEBUG_NAME = b"SeDebugPrivilege"
SE_PRIVILEGE_ENABLED = 0x00000002


# additional types

SIZE_T = ctypes.c_size_t
PSIZE_T = ctypes.POINTER(SIZE_T)
PHANDLE = ctypes.POINTER(wintypes.HANDLE)
DWORD_PTR = SIZE_T
PVOID = wintypes.LPVOID

PPROC_THREAD_ATTRIBUTE_LIST = wintypes.LPVOID
LPPROC_THREAD_ATTRIBUTE_LIST = wintypes.LPVOID

# define the necessary structures for our token struct

# typedef struct _LUID {
#   DWORD LowPart;
#   LONG HighPart;
# } LUID,
#  *PLUID;
class LUID(ctypes.Structure):
    _fields_ = [
        ("LowPart", wintypes.DWORD),
        ("HighPart", wintypes.LONG),
    ]


PLUID = ctypes.POINTER(LUID)

# typedef struct _LUID_AND_ATTRIBUTES {
#   LUID Luid;
#   DWORD Attributes;
# } LUID_AND_ATTRIBUTES,
#  *PLUID_AND_ATTRIBUTES;
class LUID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("Luid", LUID),
        ("Attributes", wintypes.DWORD),
    ]


PLUID_AND_ATTRIBUTES = ctypes.POINTER(LUID_AND_ATTRIBUTES)

# typedef struct _TOKEN_PRIVILEGES {
#   DWORD PrivilegeCount;
#   LUID_AND_ATTRIBUTES Privileges[ANYSIZE_ARRAY];
# } TOKEN_PRIVILEGES,
#  *PTOKEN_PRIVILEGES;
class TOKEN_PRIVILEGES(ctypes.Structure):
    _fields_ = [
        ("PrivilegeCount", wintypes.DWORD),
        ("Privileges", LUID_AND_ATTRIBUTES),
    ]


PTOKEN_PRIVILEGES = ctypes.POINTER(TOKEN_PRIVILEGES)

# define our STARTUPINFO structure -

# typedef struct _STARTUPINFO {
#   DWORD  cb;
#   LPTSTR lpReserved;
#   LPTSTR lpDesktop;
#   LPTSTR lpTitle;
#   DWORD  dwX;
#   DWORD  dwY;
#   DWORD  dwXSize;
#   DWORD  dwYSize;
#   DWORD  dwXCountChars;
#   DWORD  dwYCountChars;
#   DWORD  dwFillAttribute;
#   DWORD  dwFlags;
#   WORD   wShowWindow;
#   WORD   cbReserved2;
#   LPBYTE lpReserved2;
#   HANDLE hStdInput;
#   HANDLE hStdOutput;
#   HANDLE hStdError;
# }STARTUPINFO, *LPSTARTUPINFO;
class STARTUPINFO(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("lpReserved", wintypes.LPSTR),
        ("lpDesktop", wintypes.LPSTR),
        ("lpTitle", wintypes.LPSTR),
        ("dwX", wintypes.DWORD),
        ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD),
        ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD),
        ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD),
        ("cbReserved2", wintypes.WORD),
        ("lpReserved2", wintypes.LPBYTE),
        ("hStdInput", wintypes.HANDLE),
        ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
    ]


# and our STARTUPINFOEX structure -

# typedef struct _STARTUPINFOEX {
#   STARTUPINFO StartupInfo;
#   PPROC_THREAD_ATTRIBUTE_LIST lpAttributeList;
# } STARTUPINFOEX,  *LPSTARTUPINFOEX;
class STARTUPINFOEX(ctypes.Structure):
    _fields_ = [
        ("StartupInfo", STARTUPINFO),
        ("lpAttributeList", PPROC_THREAD_ATTRIBUTE_LIST),
    ]


# we also have to define a quick struct for lpProcessInformation

# typedef struct _PROCESS_INFORMATION {
#     HANDLE hProcess;
#     HANDLE hThread;
#     DWORD dwProcessId;
#     DWORD dwThreadId;
# } PROCESS_INFORMATION, *PPROCESS_INFORMATION, *LPPROCESS_INFORMATION;
class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", wintypes.HANDLE),
        ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD),
    ]


LPPROCESS_INFORMATION = ctypes.POINTER(PROCESS_INFORMATION)

# and a struct for security_attributes -
# even though for now, this program doesn't use this apart from for type checking,
# so we could theoretically just set LPSECURITY_ATTRIBUTES = wintypes.LPVOID,
# but it may be useful in the future

# typedef struct _SECURITY_ATTRIBUTES {
#     DWORD nLength;
#     LPVOID lpSecurityDescriptor;
#     BOOL bInheritHandle;
# } SECURITY_ATTRIBUTES, *PSECURITY_ATTRIBUTES, *LPSECURITY_ATTRIBUTES;
class SECURITY_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("nLength", wintypes.DWORD),
        ("lpSecurityDescriptor", wintypes.LPVOID),
        ("bInheritHandle", wintypes.BOOL),
    ]


LPSECURITY_ATTRIBUTES = ctypes.POINTER(SECURITY_ATTRIBUTES)

# choose parent for a windows process -
# based on https://blog.didierstevens.com/2009/11/22/quickpost-selectmyparent-or-playing-with-the-windows-process-tree/
# and the implementation in python,
# https://github.com/MarioVilas/winappdbg/blob/master/tools/SelectMyParent.py
