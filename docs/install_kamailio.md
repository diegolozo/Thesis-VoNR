# Kamailio Installation Guide

This guide covers the installation of Kamailio as the SIP server used in this work (version 6.0.1), plus the extra steps and fixes that were needed on top of the official instructions.

## 1. Installation

Follow the official Kamailio 6.0 installation guide (from Git):

https://github.com/kamailio/kamailio-docs/blob/master/kamailio-6.0-install-guide-git/docs/index.md

### Troubleshooting: `kamdbctl.mysql` not found

If the database creation step fails because the file `kamdbctl.mysql` cannot be found, locate it first:

```bash
sudo find / -type f -name "kamdbctl.mysql" 2>/dev/null
```

Then copy it to the location where Kamailio expects it (the path shown in the error message):

```bash
sudo cp <original_path> <expected_path>
```

Where:

- `<original_path>`: where `find` located `kamdbctl.mysql`.
- `<expected_path>`: where Kamailio looks for it.

## 2. Running the service

After the installation, the Kamailio service should already be running. Check it with:

```bash
sudo systemctl status kamailio
```

Start, stop or restart it with:

```bash
sudo systemctl start kamailio
sudo systemctl stop kamailio
sudo systemctl restart kamailio
```

> **Important:** if you change `kamailio.cfg` and the service fails to start or restart, check the system log for the error:
>
> ```bash
> sudo tail -n 50 /var/log/syslog
> ```

### Start automatically at boot

```bash
sudo systemctl enable kamailio
```

## 3. Adding users

Users are added to the database with `kamctl`:

```bash
kamctl add <username> <password>
```

Example:

```bash
kamctl add 1001 <password>
kamctl add 1002 <password>
kamctl add alice <password>
```

A username can be a phone number or any other value; it becomes the user part of the SIP URI (for example, `sip:1001@<server_ip>`).