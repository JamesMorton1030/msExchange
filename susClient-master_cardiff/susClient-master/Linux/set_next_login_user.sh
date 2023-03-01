#!/bin/bash

# Support for GDM3
echo "[daemon]
TimedLoginEnable=true
TimedLogin=$1
TimedLoginDelay=$2" | sudo tee /etc/gdm3/custom.conf 1>/dev/null

# Support for LightDM
echo "[Seat:*]
autologin-user=$1
autologin-user-timeout=$2
" | sudo tee /etc/lightdm/lightdm.conf.d/50-sus-custom-lightdm.conf

sudo reboot
