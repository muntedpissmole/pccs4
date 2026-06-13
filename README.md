# The Pissmole Camper Control System

## Overview
The Pissmole Camping Control System (PCCS) is a Raspberry Pi-based control system for managing RV/camper trailer lighting and environmental data. It provides:
- Control of dimmable lighting and on/off relays
- Swapping between white and red (anti-bug) modes for kitchen and awning lights
- Lighting scenes such as bedtime, bathroom and all off
- Time-of-day phase calculation (day, evening and night) and accurate sunset/sunrise times based on GPS derived co-ordinates
- Reed switch monitoring of panel doors that switch on linked lights to levels based on time-of-day/phase
- Ambient lighting such as accent and awning that turn on whenever any panel is open
- Protection against turning on the rooftop tent lights when closed where the LED strip may be pressed against bedding
- Comprehensive logging that shows what light turned on and what activated it (phase change, scene, reed, user interface etc.)
- A flexible & scalable UI that can be accessed from any device including touchscreens, tablets and phones
- Full support for Cloudflare Tunnels for if the Internet connection is behind cgnat (e.g. Starlink, hotspots)
- A toast/message popup system with helpful information when events happen like GPS fix acquired/lost and phase changes
- Modern UI themes with light/dark modes including Glassmorphism/Frosted Glass, Neumorphism, Deep Minimal/Stealth and automatic toggling of light and dark modes in the evening and morning
- A System tab with diagnostics, overrides, policy explain, and additional information

The PCCS measures and displays environmental data including:
- GPS derived data & time and sunset/sunrise times based on current coordinates
- Water tank level
- Current temperature and daily min/max weather forecasts for the current location
- GPS satellite/quality fix and scraping of closest suburb based on current co-ordinates with offline/no internet fallback for greater North-East Victoria in Australia
- Battery + solar via Victron SmartShunt + MPPT SmartSolar BLE (`victron_ble` library)

The PCCS provides a better glamping experience when installed alongside other RPI packages:
- Network address translation (NAT) and DHCP via DNSMASQ. Upstream internet can be provided by USB tethering, 5G modem or Starlink
- UniFi controller for UniFi WAPs
- Pi-hole for adblocking

## Hardware
**Backend**

This project has been built with support for:
- Raspberry Pi
- Arduino Mega 2560 and IRLZ234N mosfets to ramp LEDs and the analog input for measuring water tank level
- Adafruit Ultimate GPS Breakout PA1616S
- 4 channel 5VDC relay module
- DS18B20 1-wire Temperature Sensor
- fuel level sensor that scales from 240ohm (full) to 33ohm (empty)

**Power Monitoring (Victron)**
- Victron SmartShunt (battery voltage, current, SoC, time remaining, etc.)
- Victron SmartSolar MPPT (solar power, daily yield, charge state)
- Connected over Bluetooth Low Energy using the `victron_ble` Python library (passive "Instant Readout" advertisements — no constant connection required)
- Requires a **USB Bluetooth adapter** on the Pi (onboard Bluetooth is disabled for GPS UART — see [Victron BLE setup](#victron-ble-setup) below)
- Configure MAC address + 32-character advertisement key per device in `config/pccs.conf` `[victron]` (from VictronConnect → device → gear → Product info → Instant readout via Bluetooth). The VictronConnect mesh name is not used by PCCS.

**Frontend**

 A touchscreen such as a waveshare powered by another RPI or Rock Pi for more capability in handling the intensive graphics processing.

## User Interface
#### Touchscreen/iPad/Desktop
|Glassmorphism|
|:-----------:|
|<img src="images/ipad-glass-dark-front-landscape.png">|
|Neumorphism|
|<img src="images/ipad-neumorph-dark-front-landscape.png">|

#### Portrait and Light Mode (Red indicates bug mode capable lights)
<img src="images/ipad-glass-light-front-portrait.png" width="50%">

#### Mobile
|Glassmorphism|Neumorphism|
|:-----------:|:---------:|
|<img src="images/iphone-glass-dark-front.png">|<img src="images/iphone-neumorph-dark-angle.png">|
|<img src="images/iphone-glass-light-front.png">|<img src="images/iphone-neumorph-light-angle.png">|

See /images folder for more examples.

## Wiring
#### Raspberry Pi
| Logical/BCM Pin | Physical Pin | Channel Type           | Description                               |
|:---------------:|:------------:|:-----------------------|:------------------------------------------|
| GPIO4           | 7            | 1-Wire Input           | DS18B20 Temperature Sensor                |
| GPIO8           | 24           | UART TX                | GPS Transmit                              |
| GPIO10          | 19           | UART RX                | GPS Receive                               |
| GPIO17          | 11           | Relay Module Channel 1 | Floodlights                               |
| GPIO18          | 12           | Relay Module Channel 2 | Future Water Circuit (Not in Use)         |
| GPIO22          | 15           | Relay Module Channel 3 | Future Lighting Circuit (Not in Use)      |
| GPIO27          | 13           | Relay Module Channel 4 | Future Fridge & Oven Circuit (Not in Use) |
| GPIO12          | 32           | Reed Input             | Kitchen Bench                             |
| GPIO23          | 16           | Reed Input             | Kitchen Panel                             |
| GPIO24          | 18           | Reed Input             | Storage Panel                             |
| GPIO25          | 22           | Reed Input             | Rear Drawer                               |
| GPIO26          | 37           | Reed Input             | Rooftop Tent                              |
| N/A             | N/A          | USB Port               | Arduino Mega                              |
| N/A             | N/A          | USB Port               | Bluetooth dongle (Victron BLE — see below) |

**Notes**
<small>
- 1-Wire needs to be enabled in raspi-config (see instructions below)
- Onboard Bluetooth is **disabled** (`dtoverlay=disable-bt`) so the UART is free for GPS — Victron BLE requires a **USB Bluetooth dongle** ([Victron BLE setup](#victron-ble-setup))
- 5V for peripherals (GPS/relay module etc.) not included in above table
</small>

#### Arduino Mega
**Outputs**
| Pin | Channel Type           | Description                            |
|:---:|:-----------------------|:---------------------------------------|
| 2  | PWM/Output             | Kitchen Panel RGBW LED Strip - White   |
| 3  | PWM/Output             | Kitchen Panel RGBW LED Strip - Red     |
| 4  | PWM/Output             | Kitchen Panel RGBW LED Strip - Green   |
| 5  | PWM/Output             | Kitchen Bench LED Strip                |
| 6  | PWM/Output             | Storage Panel LED Strip and Downlights |
| 7  | PWM/Output             | Rear drawer LED Strip                  |
| 8  | PWM/Output             | Accent LED Strips                      |
| 9  | PWM/Output             | Awning RGBW LED Strip - White          |
| 10 | PWM/Output             | Awning RGBW LED Strip - Red            |
| 11 | PWM/Output             | Awning RGBW LED Strip - Green          |
| 12 | PWM/Output             | Rooftop tent LED Strip                 |
| 13 | PWM/Output             | Ensuite tent LED Strip                 |

**Inputs**
| Pin | Channel Type           | Description                            |
|:---:|:-----------------------|:---------------------------------------|
| A1 | Analog Input           | Water Level Sensor Input               |

**Notes**
<small>
- Arduino Mega is used as RPI PWM/I2C servo driver expansion boards don't have enough power to drive the MOSFETs
- Breadboard circuitboard for MOSFETs and outgoing lighting circuit connections is required
- Some analog signal conditioning may still be needed for the water level sender on A1
- Blue channels of RGB lights not used in this project due to Arduino channel capacity (Green is used to soften the red)
</small>

### Other Recommended Hardware
- **USB Bluetooth dongle** (required for Victron SmartShunt / MPPT). The Pi's onboard Bluetooth is turned off at boot by `dtoverlay=disable-bt` so the GPS can use the UART — a USB adapter is the only way to get Bluetooth on the PCCS Pi. Any BLE 4.0+ dongle should work (USB Bluetooth 5.0 adapters are fine). Plug it directly into a Pi USB port if possible; avoid long or unpowered USB hubs if Victron devices are more than a few metres away.
- 12-48v PoE 5 port network switch for WAP, a wired connection to RPI and a wired connection to other lighting control touchscreens in the installation (e.g. kitchen, rooftop tent)
- Cel-Fi GO 4/5G booster

## Software Installation & Configuration
These instructions are based on the following settings:
```ini
RPI IP: 10.10.10.1
DHCP range: 10.10.10.50-10.10.10.200
Internet connection: USB hotspot or WiFi (for when system is in the workshop)
Network: Wired ethernet connection is connected to other devices (touchscreen RPI's, WAPS) in the installation and not bridged to the upstream internet connection
```

1.  Format an SD card with Debian Trixie 64-bit. Enable SSH during installation and edit all customisation options to suit.
2.  Before ejecting the SD card, open `config.txt` in the root of the boot partition on the host computer (the volume that appears when you insert the card — not a path on the running Pi).
3.  Add the following lines to the end of the file to enable GPS communication:

```ini
enable_uart=1
dtoverlay=disable-bt
dtparam=spi=on
```

`dtoverlay=disable-bt` turns off the Pi's **built-in** Bluetooth so the serial port can be used for GPS. Victron BLE still works via a **USB Bluetooth dongle** (see [Victron BLE setup](#victron-ble-setup)).

4.  Save and eject card, install into RPI and login via SSH using the account name and password set during image creation e.g. `ssh $USERNAME@192.168.0.78` (substitute your account name if you have not set `USERNAME` yet).

After your first SSH login (step 4), set the Linux account and install path for every bash snippet below:

```bash
export USERNAME=pi
export PCCS_HOME=/home/$USERNAME/pccs4
export SCREEN_USER=pi
export SCREEN_HOST=10.10.10.10
```

Change `USERNAME` if your PCCS Pi account name differs. `SCREEN_USER` and `SCREEN_HOST` must match the username and host in each `[screens]` entry in `config/pccs.conf` — see step 12.

5.  Set a static IP address for the wired ethernet port, modify details to suit:
```bash
export USERNAME=pi
export PCCS_HOME=/home/$USERNAME/pccs4

sudo nmcli connection modify "netplan-eth0" ipv4.addresses 10.10.10.1/24
sudo nmcli connection modify "netplan-eth0" ipv4.dns "1.1.1.1,1.0.0.1"
sudo nmcli connection modify "netplan-eth0" ipv4.method manual
sudo nmcli connection modify "netplan-eth0" connection.autoconnect yes
```
Reset connection for changes to take effect:
```bash
sudo nmcli connection down "netplan-eth0"
sudo nmcli connection up "netplan-eth0"
nmcli connection show "netplan-eth0"
```
The above assumes that the ethernet name is `netplan-eth0`, run `nmcli connection show` to confirm.

---
6.   Install dependencies:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install nginx samba samba-common-bin python3-venv python3-lgpio git network-manager usbmuxd libimobiledevice-utils ipheth-utils bluez -y
```

`usbmuxd`, `libimobiledevice-utils`, and `ipheth-utils` enable iPhone USB tethering (creates a `usb0`/`eth` interface when the phone is plugged in and tethering is enabled). `network-manager` is required for Wi‑Fi scan/connect in the System tab. `bluez` provides Bluetooth support for the USB dongle used by Victron BLE (usually pre-installed on Raspberry Pi OS, but listed here for completeness).

---
7.  Create project folder, navigate to it and setup permissions for `$USERNAME` and nginx:
```bash
mkdir -p "$PCCS_HOME"

cd "$PCCS_HOME"
sudo chown -R "$USERNAME":www-data "$PCCS_HOME"
sudo chmod -R 775 "$PCCS_HOME"
sudo find "$PCCS_HOME" -type d -exec chmod g+s {} \;
```

---
8.  **(Optional)** - Enable file sharing for ease of editing:

Append the Samba share (uses `$USERNAME` and `$PCCS_HOME`):
```bash
sudo tee -a /etc/samba/smb.conf > /dev/null <<EOF

[pccs4]
    path = $PCCS_HOME
    writable = yes
    browsable = yes
    public = no
    valid users = $USERNAME
    force group = www-data
    create mask = 0664
    force create mode = 0664
    directory mask = 0775
    force directory mode = 0775
    hide dot files = no
EOF
```
Set the password for the share:
```bash
sudo smbpasswd -a "$USERNAME"
```
Restart samba for changes to take effect:
```bash
sudo systemctl restart smbd nmbd
```
Access the share via the IP set in the network configuration earlier in this guide. Use username `$USERNAME` and the password set just now to browse the shares.

---
9.  Configure nginx:
```bash
sudo tee /etc/nginx/sites-available/pccs > /dev/null <<EOF
server {
    listen 80;
    server_name _;

    root $PCCS_HOME;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
        proxy_buffering off;
    }

    location /static/ {
        alias $PCCS_HOME/static/;
        expires 30d;
        add_header Cache-Control "public";
        try_files \$uri =404;
    }
}
EOF
```

Create a symlink, remove the default site config and restart nginx for changes to take effect:
```bash
sudo ln -s /etc/nginx/sites-available/pccs /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

---
10. Install Git, clone the project, install the virtual environment (venv) and install more dependencies:
```bash
git clone https://github.com/muntedpissmole/pccs4.git "$PCCS_HOME"

cd "$PCCS_HOME"
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Some pip-installed console scripts (e.g. victron-ble) can end up without the
# executable bit on Raspberry Pi OS venvs; make them runnable for the test
# commands below.
chmod +x venv/bin/victron-ble
```

Python dependencies are pinned in `requirements.txt` (runtime) and `requirements-dev.txt` (adds `pytest` for the test suite).

System packages for iPhone USB tethering (installed via `apt` above, not pip):

```
usbmuxd
libimobiledevice-utils
ipheth-utils
```

Configure GPS communications:
```bash
sudo nano /boot/firmware/cmdline.txt
```
Search for and remove these lines: `console=serial0,115200` or `console=ttyAMA0,115200`.
Press Ctrl+S to save and then Ctrl+x to exit.

Configure GPS port permissions:
```bash
sudo usermod -a -G tty,dialout "$USERNAME"
sudo chown root:tty /dev/ttyAMA0
sudo chmod 660 /dev/ttyAMA0
```

Setup communication for the temperature sensor:
```bash
sudo raspi-config
```
Go to `Interface Options` → `Enable 1-Wire` → `Finish` and then reboot.
Wait for reboot then SSH back in.

---
11. Install Arduino compiler and push sketch to Arduino:

Add Arduino compiler repo:
```bash
curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | BINDIR=/usr/local/bin sudo sh
```
Install the compiler and push the sketch (Arduino must be connected and powered on):
```bash
cd "$PCCS_HOME"
arduino-cli core install arduino:avr
arduino-cli compile --fqbn arduino:avr:mega --upload --port /dev/ttyACM0 arduino/
```

---
12. **(Optional)** Set up passwordless SSH from the PCCS Pi to remote touchscreen Pis. When a linked reed opens or closes, PCCS wakes or blanks those screens over SSH. Configure each screen under `[screens]` in `config/pccs.conf` (host, username, `brightness_path`, linked reed). Test from the **Screens** tile on the System tab.

On the PCCS Pi, logged in as `$USERNAME`:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""
ssh-copy-id $SCREEN_USER@$SCREEN_HOST
```

Repeat `ssh-copy-id` for every touchscreen Pi (update `SCREEN_USER` and `SCREEN_HOST` to match each `[screens]` entry).

Verify non-interactive login (PCCS uses the same SSH flags):

```bash
ssh -o BatchMode=yes -o PreferredAuthentications=publickey $SCREEN_USER@$SCREEN_HOST 'echo ok'
```

On each remote Pi, the SSH user must be able to write the brightness/blank sysfs file. See the notes under `[screens]` in `config/pccs.conf` if wake/sleep fails with permission errors.

---
13. Do another permissions refresh to eliminate any lingering access issues:
```bash
cd "$PCCS_HOME"
sudo chown -R "$USERNAME":www-data .
sudo chmod -R 775 .
sudo find . -type d -exec chmod g+s {} \;
sudo find . -type f -exec chmod 664 {} \;
```

---
### Victron BLE setup

If you use a Victron SmartShunt and/or MPPT SmartSolar, PCCS reads them via passive BLE advertisements (Instant Readout). This does **not** join the VictronConnect mesh — only Instant Readout must be enabled on each device, and the Pi must be within BLE range.

#### USB Bluetooth dongle (required)

GPS on the PCCS Pi uses the serial UART (`/dev/ttyAMA0`). Step 3 adds `dtoverlay=disable-bt`, which **permanently disables the Pi's built-in Bluetooth** on every boot so that UART is not shared with BT. You cannot use onboard Bluetooth and GPS at the same time — a **USB Bluetooth dongle** is required for Victron.

1. Plug a BLE-capable USB Bluetooth adapter into the Pi (any free USB port).
2. Confirm the OS sees it:

```bash
lsusb | grep -i bluetooth
hciconfig -a
```

You should see a Bluetooth entry from `lsusb` and an `hci0` interface with `Bus: USB` (not the disabled onboard controller).

3. Enable Bluetooth and bring the adapter up:

```bash
sudo systemctl enable --now bluetooth
sudo rfkill unblock bluetooth
sudo hciconfig hci0 up
bluetoothctl show
```

`bluetoothctl show` should report `Powered: yes`. If Bluetooth was **soft-blocked** (disabled in software by the OS, not a physical switch), `rfkill list` shows `Soft blocked: yes` under `hci0` and `hciconfig hci0 up` fails with an RF-kill error until you run `rfkill unblock bluetooth`.

If `hci0` is missing after plugging in the dongle, try another USB port or a different adapter — some very old Bluetooth 2.0-only dongles do not support BLE.

#### Victron device configuration

1. In **VictronConnect**, for each device (shunt and MPPT separately): device → gear → **Product info** → **Instant readout via Bluetooth** → **Show**. Note the MAC address and 32-character key.

2. Edit `config/pccs.conf` under `[victron]`:

```ini
[victron]
shunt_address = aa:bb:cc:dd:ee:ff
shunt_key     = 0123456789abcdef0123456789abcdef

mppt_address  = 11:22:33:44:55:66
mppt_key      = fedcba9876543210fedcba9876543210
```

3. Test reception before starting PCCS (from the project venv):

```bash
cd "$PCCS_HOME"
chmod +x venv/bin/victron-ble
source venv/bin/activate
victron-ble discover
victron-ble read aa:bb:cc:dd:ee:ff@0123456789abcdef0123456789abcdef
```

If `victron-ble: command not found` or `Permission denied`, the `chmod` above fixes it (a quirk that can happen with `--system-site-packages` venvs on Raspberry Pi OS).

`discover` lists nearby Victron devices broadcasting Instant Readout. `read` prints live values for one device (repeat with each MAC@key). Ctrl+C to stop.

4. After PCCS is running, confirm in the logs:

```bash
journalctl -u pccs4.service -f | grep -i victron
```

Look for `Victron BLE scanner active`. If data stays stale, re-check MAC/key, Instant Readout on the device, dongle range, and that Bluetooth is not rfkill-blocked.

---
14. Install the PCCS as a service and start it on RPI startup:
```bash
sudo tee "$PCCS_HOME.service" > /dev/null <<EOF
[Unit]
Description=The Pissmole Camper Control System
After=network.target nginx.service

[Service]
User=$USERNAME
Group=www-data
WorkingDirectory=$PCCS_HOME
ExecStart=$PCCS_HOME/venv/bin/python3 $PCCS_HOME/app.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
EOF
```
Create a symlink, reload the systemctl, enable and autostart the PCCS:
```bash
sudo systemctl link "$PCCS_HOME.service"
sudo systemctl daemon-reload
sudo systemctl enable pccs4.service
sudo systemctl start pccs4.service
sudo systemctl status pccs4.service
```

Allow the PCCS service user to run live Wi‑Fi scans and connections (without this, the System tab shows cached networks and connect may fail):
```bash
sudo usermod -aG netdev "$USERNAME"
sudo "$PCCS_HOME/scripts/install-networkmanager-perms.sh"
sudo systemctl restart pccs4.service
```

Check the status with:
```bash
sudo systemctl status pccs4
```
To make sure it started without any errors. View the live logs with:
```bash
journalctl -u pccs4.service -f
```
Access the UI via the IP address e.g. `http://10.10.10.1` or via the Cloudflare tunnel once configured. Diagnostics and overrides are on the **System** tab.

Access the log files at `\\10.10.10.1\pccs4\logs`.

### Updating the PCCS
1.  SSH into the Pi and git pull the newest version:
```bash
export USERNAME=pi
export PCCS_HOME=/home/$USERNAME/pccs4

cd "$PCCS_HOME"
git pull
source venv/bin/activate
pip install -r requirements.txt

# Ensure victron-ble (and any other entry-point scripts) are executable.
chmod +x venv/bin/victron-ble
```

Update the Pi OS at the same time:
```bash
sudo apt update && sudo apt upgrade -y
```

Reboot if asked, otherwise restart the PCCS service:
```bash
sudo systemctl restart pccs4
```

### Run Application Manually

Stop the service (if installed/running):
```bash
sudo systemctl stop pccs4.service
```
Navigate to project folder, start a virtual environment and the PCCS:
```bash
export USERNAME=pi
export PCCS_HOME=/home/$USERNAME/pccs4

cd "$PCCS_HOME"
source venv/bin/activate
python app.py
```

## Other Setup:
### NAT/Routing/Internet
1. Edit the DHCP config file:
```bash
sudo nano /etc/dhcpcd.conf
```
Paste at the bottom:
```ini
# LAN - Wired clients
interface eth0
static ip_address=10.10.10.1/24
nohook wpa_supplicant

# USB tethering/hotspot
interface usb0
metric 50

# WiFi
interface wlan0
metric 200
```
Press Ctrl+S to save and then Ctrl+x to exit.

2.  Edit the DNS config file:
```bash
sudo nano /etc/dnsmasq.conf
```
Search for, uncomment and update the following lines or just paste everything at the end of the file:
```ini
interface=eth0
bind-interfaces
except-interface=wlan0
except-interface=usb0

dhcp-range=10.10.10.50,10.10.10.200,255.255.255.0,12h

dhcp-option=3,10.10.10.1
dhcp-option=6,10.10.10.1
```
Press Ctrl+S to save and then Ctrl+x to exit.


3.  Enable IP forwarding. Edit the sysctl config file:
```bash
sudo nano /etc/sysctl.conf
```
Uncomment this line or add it to the bottom of the file:
```ini
net.ipv4.ip_forward=1
```
Press Ctrl+S to save and then Ctrl+x to exit.

Apply the updated config:
```bash
sudo sysctl -p
```

Setup and configure NAT forwarding rules:
```bash
sudo iptables -t nat -A POSTROUTING -o usb0 -j MASQUERADE
sudo iptables -t nat -A POSTROUTING -o wlan0 -j MASQUERADE

sudo iptables -A FORWARD -i eth0 -o usb0 -j ACCEPT
sudo iptables -A FORWARD -i eth0 -o wlan0 -j ACCEPT
sudo iptables -A FORWARD -i usb0 -o eth0 -m state --state RELATED,ESTABLISHED -j ACCEPT
sudo iptables -A FORWARD -i wlan0 -o eth0 -m state --state RELATED,ESTABLISHED -j ACCEPT
```

Write the rules permanently the the network configuration:
```bash
sudo netfilter-persistent save
```

Restart everything:
```bash
sudo systemctl restart dhcpcd
sudo systemctl restart dnsmasq
sudo systemctl enable dnsmasq
```

Reboot the RPI with `sudo reboot` and login again after it's rebooted.
Check interface configuration looks correct:
```bash
ip addr show
ip route show
```

Make sure DHCP is only listening on the wired network card:
```bash
sudo ss -tulnnp | grep dnsmasq
```

See if the internet works:
```bash
ping -c 8.8.8.8
```

### UniFi OS Server
1.  Go to the [Unifi software download page](https://ui.com/download/software/unifi-os-server), right click the Linux arm64 download link and copy the link.

2.  Download the installer:
```bash
wget -O unifiosinstaller [PASTE THE COPIED LINK HERE]
```

3.  Make it executable and run the installer:
```bash
sudo chmod +x unifiosinstaller
sudo ./unifiosinstaller
```

4.	Give the server admin rights:
```bash
export USERNAME=pi
sudo usermod -aG uosserver "$USERNAME"
```

Access the UI on `https://10.10.10.1:11443`.
