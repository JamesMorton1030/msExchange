# Hotdesking + AD accounts are currently not working. SUS will only work with local user accounts at this current time.

## Install instructions for Ubuntu 20.04:
Note: Not all applications support Linux. Ensure when schedules are set up, that applications that support Linux are selected.

###  Setup display manager 
Note: Both GDM3 + LightDM are supported, I have used LightDM as it supports VNC on the login screen. The installation scripts support both of them and require no additional configuration for either one.

It's highly recommended to use lightdm:
- Run `sudo apt install lightdm`
- When prompted, select lightdm as the display manager

### Install SUS files
- Configure windows server settings in install_sus.sh
- Run `sudo ./install_sus.sh`
- Run `sudo systemctl enable x11vnc-gdm` for GDM or `sudo systemctl enable x11vnc-lightdm` for LightDM depending on display manager

### Set up Active Directory:
- Ensure DNS settings is configured to the windows server
- Run the commands below, modifying `sustest.internal` with the domain in AD
```bash
sudo apt install realmd
sudo realm join sustest.internal --user susadmin
sudo pam-auth-update --enable mkhomedir
```
- Edit `/etc/sssd/sssd.conf` with content below, modifying `sustest.internal`  with the domain in AD
```
[sssd]
domains = sustest.internal
config_file_version = 2
services = nss, pam

[domain/sustest.internal]
create_homedir = True
default_shell = /bin/bash
krb5_store_password_if_offline = True
cache_credentials = True
krb5_realm = SUSTEST.INTERNAL
realmd_tags = manages-system joined-with-adcli 
id_provider = ad
override_homedir = /home/%d/%u
ad_domain = sustest.internal
use_fully_qualified_names = False
ldap_id_mapping = True
access_provider = ad
```

### Setup browser drivers
- Download chromedriver + geckodriver and place them on the windows share (/sus will automatically be added to PATH)
- Ensure permissions are set correctly:
```
chown 777 geckodriver
chown 777 chromedriver
```