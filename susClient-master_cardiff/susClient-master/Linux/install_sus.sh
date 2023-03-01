#!/bin/bash
	
WINDOWS_SERVER="10.0.0.6"
# User/pass to access the NTFS drive with
WINDOWS_SERVER_USER="susadmin"
WINDOWS_SERVER_PASS="CorrectHorseBatteryStaple1!"

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 
   exit 1
fi

echo "Installing SUS..."

# Empty log file
echo "" > sus_installation.log

# Backup gdm3 custom conf
echo "Backing up /etc/gdm3/custom.conf at /etc/gdm3/custom.conf.backup"
mv /etc/gdm3/custom.conf /etc/gdm3/custom.conf.backup

echo "Creating empty file at /etc/gdm3/custom.conf"
touch /etc/gdm3/custom.conf

# Create empty file for lightdm
echo "Creating empty file at /etc/lightdm/lightdm.conf.d/50-sus-custom-lightdm.conf"
touch /etc/lightdm/lightdm.conf.d/50-sus-custom-lightdm.conf

# Setup script + permissions
echo "Installing hotdesking script at /usr/local/bin/set_next_login_user.sh"
cp ./set_next_login_user.sh /usr/local/bin/set_next_login_user.sh
echo "ALL ALL=NOPASSWD: /usr/local/bin/set_next_login_user.sh" >> /etc/sudoers

# Setup network share
echo "Installing cifs-utils for mounting Windows network drive"
apt install cifs-utils 1>sus_installation.log 2>sus_installation.log
mkdir /sus

# Setup auto-mount
echo "Writing windows mount into /etc/fstab"
echo "//$WINDOWS_SERVER/sus  /sus  cifs  username=$WINDOWS_SERVER_USER,password=$WINDOWS_SERVER_PASS,file_mode=0677,dir_mode=0677" >> /etc/fstab

# Add to path
echo "Add /sus to PATH"
echo 'PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin:/sus"' > /etc/environment

# Setup lockscreen stuff...
echo "Disabling auto lock after inactivity..."
gsettings set org.gnome.desktop.screensaver lock-enabled 'false'

echo "Disabling screen going blank..."
gsettings set org.gnome.desktop.session idle-delay 0

echo "Installing run-sus.desktop autostart application"
cp ./run-sus.desktop /etc/xdg/autostart/run-sus.desktop

# Install VNC
echo "Installing VNC services (x11vnc-gdm & x11vnc-lightdm)"
apt install x11vnc 1>sus_installation.log 2>sus_installation.log
cp ./x11vnc-gdm.service /lib/systemd/system/x11vnc-gdm.service
cp ./x11vnc-lightdm.service /lib/systemd/system/x11vnc-lightdm.service
systemctl daemon-reload