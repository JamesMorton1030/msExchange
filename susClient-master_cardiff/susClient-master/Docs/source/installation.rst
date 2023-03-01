Client Installation
===================

This document details the installation process which is required to install the client program and all of its prerequisites.

Python
******
The client program was developed to run using python, specifically we used version 3.7.5 (x64). The installation files we used were downloaded from the python `website <https://www.python.org/downloads/release/python-375/>`_ and we opted for the web installer. During the installation process choose custom installation to make sure that everything is setup correctly. On the next page we unchecked the *python test suite* and *tcl/tk support* as both of those are unnecessary for the client program. The pages after that are more important as the options for *install for all users* and *add to path* need to be checked for the program to work.

SUS Client
**********
The client is made up of a number of different programs which are downloaded as one set. We recommend downloading them to ``C:\Program Files\SUS`` such that the AUS, Hotdesking etc. folders are at the root of that directory, as that is a logical location which can be accessed by all users of the system. While the AUS portion of SUS may be installed at any location, it is strongly recommended to install Hotdesking in the above path due to some limitations in its current implementation. Please see below for a list of files which need to be edited in order to move SUS's location.

Once the files have been downloaded you can install the hotdesking module by running the ``install.bat`` file which is in the hotdesking folder of the client installation files. This will install all the required python packages and also make some of the necessary registry edits for the hotdesking module to run. Finally, open ``services.msc`` and set the ``SUSHotdesking`` service to run automatically.

User Simulator
**************
The user simulation part of the program currently does not have an automated installation process and has to be installed manually. The first part of this is installing the required python packages by going into the AUS folder of the client and running the command ``pip install -r requirements.txt``. In order to complete the installation of the pywin32 package a post installation script needs to be run with the command ``python "C:\Program Files\Python37\Scripts\pywin32_postinstall.py" -install``.

To finish the installation process the client also needs to be setup to run on startup for each user. The simplest way of doing this appears to be to make a shorcut to the program in the windows startup folder which is then called whenever the user logs in. An alternative method which could also work is using group policy objects and active directory to configure the program to start each time.

Browsers
********
The client currently fully supports Chrome and Firefox, with support for Edge being worked on.

Chrome can be downloaded from Google's `website <https://www.google.com/chrome/>`_ and the installation process is as simple as running the executable. For chrome to be controlled automatically the chrome webdriver also needs to be downloaded from the chromium `website <https://chromedriver.chromium.org/downloads>`_. Make sure when selecting which version to download it matches the installed version of chrome otherwise it will not work. This webdriver will need to placed somewhere on the PATH, one solution for this is to place the file in System32. However a better solution would be to make a new folder and then to add that to PATH.

Firefox is available from Mozilla's `website <https://www.mozilla.org/en-GB/firefox/new/>`_ and like chrome we opted to use the default installation options. Firefox also needs a webdriver to function properly and this is available from Mozilla's `github <https://github.com/mozilla/geckodriver/releases>`_. The downloaded executable will also have to be placed somewhere on the PATH for it to be used.

Edge is included with windows but like Chrome and Firefox will also need a webdriver to function. Provided the version of Edge is 18 or above, enabling developer mode in Windows Settings will install the webdriver. Older versions must use the standalone driver. This can be downloaded from Microsoft's `website <https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/>`_ however you need to download the versions for *Legacy Edge* as Microsoft have since released the chromium variant of edge which has a different webdriver. Once this has been downloaded it will also need to be placed on the PATH. In addition to this, a registry key will need to be provided in order to disable the first run experience of the new Edge. HKLM\SOFTWARE\Policies\Microsoft\Edge\HideFirstRunExperience should be set to 1. See <https://docs.microsoft.com/en-us/deployedge/microsoft-edge-policies#hidefirstrunexperience>

Microsoft Office
****************
Installing Microsoft Office is a complicated process however we opted to do this using Office Deployment Tool which is available free from `here <https://www.microsoft.com/en-us/download/details.aspx?id=49117>`_. Running the executable will ask you where to extract some files and these can be placed anywhere as they are only needed once. The tool uses an XML config file to configure how to install office and one called ``office.xml`` is included in the examples folder. These XML files can be configured using this `tool <https://config.office.com/deploymentsettings>`_ however we recommend trying to avoid changing the example XML too much. In order to use the deployment tool open the folder where the files where extracted to and copy the ``office.xml`` file into that folder. Open command prompt in that folder and then run two commands: ``setup.exe /download office.xml`` which downloads the installation files and then ``setup.exe /configure office.xml`` which sets up office and installs everything.

Git Command
***********
Installing the git command is simple as we opted to use the default settings. The installer can be downloaded from `here <https://git-scm.com/download/win>`_ and then to install the program we just clicked next through all the options and left everything as default.

Adobe Reader
************
Adobe Reader was another simple to install application as it is not very configurable so it was as simple as downloading it from this `website <https://get.adobe.com/uk/reader/otherversions/>`_ and then running the executable.

Sysmon Installation
*******************

Instructions for setting up sysmon have been compiled by Michael and are in the examples folder in a file called ``Sysmon_install_guide.txt``.

Annex: Installing the client to an alternate location
*****************************************************
Files to be edited:
Hotdesking:
	NOTE: If this is to be moved to a different drive, the drive must be mounted to the VM from boot. Use of a network drive which is mounted after logon is not supported.
1. AutoLogon.py. Change CONFIG_FILE_PATH to the appropriate absolute path of the general.json config file.
2. login.cmd. Change the path provided as an argument to cscript to the absolute path of the login.vbs file.
3. unlock.cmd. Change the path, as above, to be the absolute path of the unlock.vbs file
