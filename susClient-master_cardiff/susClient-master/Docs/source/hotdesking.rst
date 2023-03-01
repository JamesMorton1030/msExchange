Hotdesking
==========

Introduction
************

The hotdesking module allows multiple users to use each Virtual Machine. On boot, it requests credentials and a wait period from the susServer. Once the wait period has elapsed, it launches a script which enters the credentials and logs the specified user in. It also supports unlocking functionality.

Installation
************
There is an install.bat script supplied with the code, which must be run as Administrator. This should set up hotdesking to work out-of-the-box. Hotdesking must be placed at C:\Program Files\SUS\Hotdesking\ , with a config file in C:\Program Files\SUS\AUS\config.json.
The install.bat script does the following:
	1) Adds a registry key to disable the ``LockApp.exe``, preventing it from stealing focus.
	2) Installs the requirements for hotdesking to run
	3) Installs hotdesking as a service on the machine

Once this has run, the service must be set to run automatically (without delay) in services.msc. The service name is SUSHotdesking.

Configuration
*************

The AUS/config.json file is used for configuring hotdesking settings.


Hotdesk Settings:
*****************
These are settings which can be changed without risk to the functionality of hotdesking.

``use_psexec``: This is an experimental setting which uses psexec to run the login/unlock scripts. It is recommended that this is set to false.

``use_local_credentials``: If this is set to true, hotdesking will not request credentials from the server and will instead use the values stored in ``default_credentials``

``profile_tags``: This allows for filtering of profiles for use on a machine, for example if a machine is in the ``IT`` group, a tag can be set to limit the profiles to only be those within that group. This should be formatted in JSON, as it passes the key directly to the server for parsing. The server then matches the values with the relevant profile tags in the user database and returns the matching set of credentials.

``log_X_local``: These keys determine whether to log the relevant files (activity, debug) locally. This can be used in addition to remote logging.

``local_X_log_file``: The path to the local log files.

``X_logging_enabled``: These keys determine whether to log the relevant files (activity, debug) remotely. This can be used in addition to local logging.

``X_logging_endpoint``: The path to the relevant susServer remote logging endpoint


Login/Unlock Vars:
******************
It is recommended that these settings are not altered.

``process_to_impersonate``: This tells hotdesking which process to duplicate tokens from.

``path_to_psexec``: The path to the local install of PSExec. This can be changed to wherever the install location is. This key is unused if ``use_psexec`` is set to false.

``psexec_args``: The arguments that should be passed to PSExec. These should not need to be changed. This key is unused if ``use_psexec`` is set to false.

``login/unlock_program``: This points towards the CMD executable. This should not need to be changed.

``login/unlock_args``: These are the arguments passed to CMD. The path to the scripts can be switched between the login.cmd and unlock.cmd without issue, should an altered setup be needed. See below for explaination of these scripts.

Default Credentials:
These can be changed to point to a local user if the susServer is not configured for hotdesking.

``username``: The username of the local user.

``password``: The plaintext password of the local user.

``delay``: The time hotdesking should wait before attempting to log in the user. This will also be the time that it waits once logged out before logging back in again.


Login and Unlock Script Explaination

login.cmd: This script is designed for the ``Other User`` screen, where the user must type both a username and password in order to log in to windows.

unlock.cmd: This is designed for the generic ``Unlock`` screen, where a user only has to type a password in order to unlock the PC. It is possible that this can be used to also login, in cases where there is a single user on the computer. However, the reccomended setup is to set windows to force the ``Other User`` screen on logout.
