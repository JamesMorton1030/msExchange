@ECHO OFF
cd "C:\Program Files\SUS\Hotdesking"
ECHO Disabling LockApp.exe
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\Personalization" /v "NoLockScreen" /t REG_DWORD /d 00000001 /f
ECHO Installing python requirements
pip install -r requirements.txt
ECHO Installing Hotdesking Service
python AutoLogon.py install
