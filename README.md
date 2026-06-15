
# The Pissmole Camper Control System

## Overview

The Pissmole Camping Control System (PCCS) is a Raspberry Pi-based control system for managing RV/camper trailer lighting and environmental data.

**Lighting and control**
-   Control of dimmable lighting and on/off relays
-   Swapping between white and red (anti-bug) modes for kitchen and awning lights
-   Lighting scenes such as bedtime, bathroom and all off
-   Time-of-day phase calculation (day, evening and night) and accurate sunset/sunrise times based on GPS derived co-ordinates
-   Reed switch monitoring of panel doors that switch on linked lights to levels based on time-of-day/phase
-   Support for turning on/off touchscreen screens that are mounted behind reed-monitored panels doors to save battery and screen burn-in
-   Ambient lighting such as accent and awning that turn on whenever any panel is open
-   Protection against turning on the rooftop tent lights when closed where the LED strip may be pressed against bedding
-   Comprehensive logging that shows what light turned on and what activated it (phase change, scene, reed, user interface etc.)
-   A flexible & scalable UI that can be accessed from any device including touchscreens, tablets and phones
-   Full support for Cloudflare Tunnels for if the Internet connection is behind cgnat (e.g. Starlink, hotspots)
-   A toast/message popup system with helpful information when events happen like GPS fix acquired/lost and phase changes
-   Modern UI themes with light/dark modes (see examples below)
-   A diagnostics and settings page with extensive override controls and additional information

**Environmental data**

- GPS location, time, and sunrise/sunset from current coordinates
- Water tank level
- Temperature and daily min/max weather forecasts for the current location
- GPS fix quality and nearest suburb (offline fallback for north-east Victoria, Australia)
- Battery and solar via Victron SmartShunt and MPPT SmartSolar

The PCCS provides a better glamping experience when installed alongside other RPI packages:

- NAT and DHCP for upstream internet via USB/WiFi hotspot, 5G modem or Starlink
- UniFi controller for UniFi WAPs
- Pi-hole for ad blocking

---

## Hardware

### Backend

Built for:

- Raspberry Pi
- Arduino Mega 2560 and IRLZ44N MOSFETs for LED PWM and analog water tank level
- Adafruit Ultimate GPS Breakout PA1616S
- 4-channel 5 VDC relay module
- DS18B20 1-Wire temperature sensor
- Fuel level sensor that scales from 240ohm (full) to 33ohm (empty) for the water tanks
- Victron SmartShunt — battery voltage, current, SoC, time remaining, etc.
- Victron SmartSolar MPPT — solar power, daily yield, charge state

### Frontend

A Waveshare (or similar) touchscreen (kitchen touchscreen in this project) on a separate Raspberry Pi or Rock 5c board for better graphics handling.

### Other hardware

- USB Bluetooth dongle (required for Victron equipment). Onboard Bluetooth disabled so that the GPS can use the UART which is the same port the onboard Bluetooth uses
- 12–48 V PoE 5-port switch — WAP, PCCS, and wired touchscreens (e.g. kitchen, rooftop tent)
- Cel-Fi GO 4G/5G booster

---

## User interface

The UI runs on touchscreens, tablets, and phones. Red indicators mark bug-mode-capable lights.

<table>
  <tr>
    <td align="center"><img src="images/ipad_neumorphism_dark_home_landscape.png" alt="Neumorphism dark — iPad landscape"></td>
  </tr>
  <tr>
    <td align="center"><strong>Neumorphism (Dark)</strong></td>
  </tr>
  <tr>
    <td align="center"><img src="images/ipad_neumorphism_light_home_landscape.png" alt="Neumorphism light — iPad landscape"></td>
  </tr>
  <tr>
    <td align="center"><strong>Neumorphism (Light)</strong></td>
  </tr>
  <tr>
    <td align="center"><img src="images/ipad_glassmorphism_dark_home_landscape.png" alt="Glassmorphism dark — iPad landscape"></td>
  </tr>
  <tr>
    <td align="center"><strong>Glassmorphism (Dark)</strong></td>
  </tr>
  <tr>
    <td align="center"><img src="images/ipad_glassmorphism_dark_lighting_landscape.png" alt="Glassmorphism dark — iPad lighting"></td>
  </tr>
  <tr>
    <td align="center"><strong>Glassmorphism (Dark) — Lighting</strong></td>
  </tr>
</table>

<table>
  <tr>
    <td align="center" width="50%"><img src="images/iphone_neumorphism_dark_home_portrait.png" alt="Neumorphism dark — iPhone portrait" height="407"></td>
    <td align="center" width="50%"><img src="images/iphone_neumorphism_dark_home_landscape.png" alt="Neumorphism dark — iPhone landscape"></td>
  </tr>
</table>

### Additional themes

<table>
  <tr>
    <td align="center" width="50%"><img src="images/themes/claymorphism.png" alt="Claymorphism" title="Claymorphism"></td>
    <td align="center" width="50%"><img src="images/themes/cyberpunk.png" alt="Cyberpunk" title="Cyberpunk"></td>
  </tr>
  <tr>
    <td align="center"><strong>Claymorphism</strong><br></td>
    <td align="center"><strong>Cyberpunk</strong><br></td>
  </tr>
  <tr>
    <td align="center"><img src="images/themes/ember.png" alt="Ember" title="Ember"></td>
    <td align="center"><img src="images/themes/industrial.png" alt="Industrial" title="Industrial"></td>
  </tr>
  <tr>
    <td align="center"><strong>Ember</strong><br></td>
    <td align="center"><strong>Industrial</strong><br></td>
  </tr>
  <tr>
    <td align="center"><img src="images/themes/nebula.png" alt="Nebula" title="Nebula"></td>
    <td align="center"><img src="images/themes/oled_minimal.png" alt="OLED Minimal" title="OLED Minimal"></td>
  </tr>
  <tr>
    <td align="center"><strong>Nebula</strong><br></td>
    <td align="center"><strong>OLED Minimal</strong><br></td>
  </tr>
  <tr>
    <td align="center"><img src="images/themes/obsidian.png" alt="Obsidian" title="Obsidian"></td>
    <td align="center"><img src="images/themes/terminal.png" alt="Terminal" title="Terminal"></td>
  </tr>
  <tr>
    <td align="center"><strong>Obsidian</strong><br></td>
    <td align="center"><strong>Terminal</strong><br></td>
  </tr>
  <tr>
    <td align="center" colspan="2"><img src="images/themes/void.png" alt="Void" title="Void"></td>
  </tr>
  <tr>
    <td align="center" colspan="2"><strong>Void</strong><br></td>
  </tr>
</table>

More examples in the [`/images`](images/) folder.

---

## Wiring

### Raspberry Pi

| Logical/BCM | Physical | Channel type | Description |
|:-----------:|:--------:|:-------------|:------------|
| GPIO4 | 7 | 1-Wire input | DS18B20 temperature sensor(s) |
| GPIO8 | 24 | UART TX | GPS transmit |
| GPIO10 | 19 | UART RX | GPS receive |
| GPIO17 | 11 | Relay 1 | Floodlights |
| GPIO18 | 12 | Relay 2 | Future water circuit *(not currently in use)* |
| GPIO22 | 15 | Relay 3 | Future lighting circuit *(not currently in use)* |
| GPIO27 | 13 | Relay 4 | Future fridge and oven circuit *(not currently in use)* |
| GPIO12 | 32 | Reed input | Kitchen bench |
| GPIO23 | 16 | Reed input | Kitchen panel |
| GPIO24 | 18 | Reed input | Storage panel |
| GPIO25 | 22 | Reed input | Rear drawer |
| GPIO26 | 37 | Reed input | Rooftop tent |
| — | USB | Serial | Arduino Mega |
| — | USB | — | Bluetooth dongle |

**Notes**

- Temp sensors need 1-Wire comms enabled in `raspi-config` during [installation](#software-installation--configuration) (step 10).
- Victron equipment needs a USB Bluetooth dongle ([Victron setup](#victron-setup)).
- 5 V for peripherals (GPS, relay module, etc.) is not shown in the table above.

### Arduino Mega

**Outputs**

| Pin | Channel type | Description |
|:---:|:-------------|:------------|
| 2 | PWM/output | Kitchen panel RGBW — white |
| 3 | PWM/output | Kitchen panel RGBW — red |
| 4 | PWM/output | Kitchen panel RGBW — green |
| 5 | PWM/output | Kitchen bench LED strip |
| 6 | PWM/output | Storage panel LED strip and downlights |
| 7 | PWM/output | Rear drawer LED strip |
| 8 | PWM/output | Accent LED strips |
| 9 | PWM/output | Awning RGBW — white |
| 10 | PWM/output | Awning RGBW — red |
| 11 | PWM/output | Awning RGBW — green |
| 12 | PWM/output | Rooftop tent LED strip |
| 13 | PWM/output | Ensuite tent LED strip |

**Inputs**

| Pin | Channel type | Description |
|:---:|:-------------|:------------|
| A1 | Analog input | Water tank sender |

**Notes**

- Arduino Mega is used as RPI PWM/I2C servo driver expansion boards don't have enough power to drive the MOSFETs
- Breadboard circuitboard for MOSFETs and outgoing lighting circuit connections is required.
- Some analog conditioning may still be needed for the water tank sender on A1.
- Blue RGB channels are unused (Arduino pin budget); green softens red bug mode.

---

## Installation

### Software installation & configuration

These instructions use the following network layout (adjust to match your site, but keep values consistent across `nmcli`, dnsmasq, and `config/pccs.conf`):

```ini
RPI IP: 10.10.10.1
DHCP range: 10.10.10.50-10.10.10.200
Kitchen touchscreen (reserved): 10.10.10.10
Internet connection: USB hotspot or WiFi
LAN Network: Wired ethernet port
```

1. Format an SD card with **Debian Trixie 64-bit** (or Raspberry Pi OS 64-bit). Enable SSH during imaging and set customization options to suit.

2. Before ejecting the SD card, open `config.txt` in the root of the boot partition on the host computer and add these lines to enable GPS communication:

```ini
enable_uart=1
dtoverlay=disable-bt
dtparam=spi=on
```

3. Save and eject the card, boot the Pi, and log in via SSH, e.g. `ssh $USERNAME@192.168.0.78`.

Set the Linux account and install path for every bash snippet below:

```bash
export USERNAME=pi
export PCCS_HOME=/home/$USERNAME/pccs4
export SCREEN_USER=pi
export SCREEN_HOST=10.10.10.10
```

Change `USERNAME` if your PCCS Pi account name differs. `SCREEN_USER` and `SCREEN_HOST` must match the username and host in each `[screens]` entry in `config/pccs.conf` — see step 12.

4. Set a static IP for the wired ethernet port (modify to suit):

```bash
export USERNAME=pi
export PCCS_HOME=/home/$USERNAME/pccs4

sudo nmcli connection modify "netplan-eth0" ipv4.addresses 10.10.10.1/24
sudo nmcli connection modify "netplan-eth0" ipv4.dns "1.1.1.1,1.0.0.1"
sudo nmcli connection modify "netplan-eth0" ipv4.method manual
sudo nmcli connection modify "netplan-eth0" connection.autoconnect yes
```

Reset the connection for changes to take effect:

```bash
sudo nmcli connection down "netplan-eth0"
sudo nmcli connection up "netplan-eth0"
nmcli connection show "netplan-eth0"
```

The above assumes the ethernet connection is named `netplan-eth0`. Run `nmcli connection show` to confirm.

---

5. Install dependencies:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install nginx samba samba-common-bin python3-venv python3-lgpio git network-manager dnsmasq usbmuxd libimobiledevice-utils ipheth-utils bluez -y
```

6. Create the project folder and set permissions for `$USERNAME` and nginx:

```bash
mkdir -p "$PCCS_HOME"

cd "$PCCS_HOME"
sudo chown -R "$USERNAME":www-data "$PCCS_HOME"
sudo chmod -R 775 "$PCCS_HOME"
sudo find "$PCCS_HOME" -type d -exec chmod g+s {} \;
```

---

7. Enable Samba file sharing for easier editing:

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

Set the share password:

```bash
sudo smbpasswd -a "$USERNAME"
```

Restart Samba:

```bash
sudo systemctl restart smbd nmbd
```

Browse the share at the IP from step 5 (`\\10.10.10.1\pccs4`). Use username `$USERNAME` and the password set above.

---

8. Configure nginx:

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

Enable the site and restart nginx:

```bash
sudo ln -s /etc/nginx/sites-available/pccs /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

---

9. Clone the project, create the virtual environment, and install Python dependencies:

```bash
git clone https://github.com/muntedpissmole/pccs4.git "$PCCS_HOME"

cd "$PCCS_HOME"
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Runtime dependencies: `requirements.txt`. Dev/test: `requirements-dev.txt` (adds `pytest`).

**GPS serial**

```bash
sudo nano /boot/firmware/cmdline.txt
```

Remove `console=serial0,115200` or `console=ttyAMA0,115200`. Save and exit.

**GPS port permissions**

```bash
sudo usermod -a -G tty,dialout "$USERNAME"
sudo chown root:tty /dev/ttyAMA0
sudo chmod 660 /dev/ttyAMA0
```

**1-Wire temperature sensors**

```bash
sudo raspi-config
```

Interface Options → Enable 1-Wire → Finish, then reboot.

After reboot, list sensor IDs:

```bash
ls /sys/bus/w1/devices/ | grep ^28
```

You should see folders like `28-000000xxxxxx`. Use these for `outside_temp_sensor`, `fridge_temp_sensor`, etc. in `config/pccs.conf`.

---

10. Install the Arduino CLI and upload the sketch (Arduino powered and connected):

```bash
curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | BINDIR=/usr/local/bin sudo sh

cd "$PCCS_HOME"
arduino-cli core install arduino:avr
arduino-cli compile --fqbn arduino:avr:mega --upload --port /dev/ttyACM0 arduino/
```

---

11. Set up remote touchscreen Pis for PCCS screen wake/sleep over SSH.

Each screen needs a fixed LAN address matching its `[screens]` entry in `config/pccs.conf` (e.g. kitchen → `10.10.10.10`). Touchscreens use DHCP on eth0; PCCS reserves their IPs in dnsmasq.

Reserve touchscreen IPs:

1. Find each screen's Ethernet MAC while it is on the LAN:

```bash
cat /var/lib/misc/dnsmasq.leases
# columns: expiry  MAC  current_ip  hostname  client_id
```

2. Add a `dhcp-host=` line per screen in `config/dnsmasq/50-pccs-screens.conf`:

```ini
# MAC from dnsmasq.leases, IP must match [screens] host in config/pccs.conf
dhcp-host=52:58:15:8a:56:f6,10.10.10.10,kitchen,infinite
```

3. Install the reservations (see [Scripts](#scripts) — `install-dnsmasq-screens.sh`):

```bash
sudo "$PCCS_HOME/scripts/install-dnsmasq-screens.sh"
```

4. On each touchscreen, renew DHCP (reboot, or `sudo nmcli device reapply eth0` / replug Ethernet). Confirm the reserved address:

```bash
ip -4 addr show eth0
ping -c1 10.10.10.1
```

Pair each panel — configure `[screens]` in `config/pccs.conf` (host, username, `brightness_path`, phase dim levels, linked reed), then run `setup-screen.sh` once per panel (see [Scripts](#scripts)). Test from the **Screens** tile on the System tab.

```bash
export SCREEN_USER=pi   # must match [screens] username
export SCREEN_HOST=10.10.10.10
"$PCCS_HOME/scripts/setup-screen.sh"
```

Set `brightness_path` in `config/pccs.conf` to match the remote OS:

- **Armbian + KDE Plasma / Wayland** (e.g. ROCK 5C): `dbus:org.kde.ScreenBrightness:/org/kde/ScreenBrightness/display0` — use phase dim levels plus `blank_path` (see `[screens]` notes). List displays with `busctl --user tree org.kde.ScreenBrightness` on the remote.
- **Radxa OS / sysfs fb blank**: `/sys/class/graphics/fb0/blank`

See notes under `[screens]` in `config/pccs.conf` if wake/sleep still fails.

---

12. Refresh permissions after clone:

```bash
cd "$PCCS_HOME"
sudo chown -R "$USERNAME":www-data .
sudo chmod -R 775 .
sudo find . -type d -exec chmod g+s {} \;
sudo find . -type f -exec chmod 664 {} \;
```

---

### Victron setup

If you use a Victron SmartShunt and/or MPPT SmartSolar, PCCS reads them via passive Instant Readout so Instant Readout must be enabled on each device and the Pi must be within range.

#### USB Bluetooth dongle (required)

GPS on the PCCS Pi uses the serial UART (`/dev/ttyAMA0`). Step 3 adds `dtoverlay=disable-bt`, which **permanently disables the Pi's built-in Bluetooth** on every boot so that UART is not shared with BT. You cannot use onboard Bluetooth and GPS at the same time — a **USB Bluetooth dongle** is required for Victron.

1. Plug a BLE-capable USB Bluetooth adapter into the Pi.
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

`bluetoothctl show` should report `Powered: yes`. If Bluetooth was **soft-blocked**, `rfkill list` shows `Soft blocked: yes` under `hci0` until you run `rfkill unblock bluetooth`.

If `hci0` is missing after plugging in the dongle, try another USB port or adapter — some Bluetooth 2.0-only dongles do not support BLE.

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
chmod +x venv/bin/victron
source venv/bin/activate
victron discover
victron read aa:bb:cc:dd:ee:ff@0123456789abcdef0123456789abcdef
```

If `victron: command not found` or `Permission denied`, the `chmod` above fixes it (a quirk with `--system-site-packages` venvs on Raspberry Pi OS).

`discover` lists nearby Victron devices broadcasting Instant Readout. `read` prints live values for one device (repeat with each MAC@key). Ctrl+C to stop.

4. After PCCS is running, confirm in the logs:

```bash
journalctl -u pccs4.service -f | grep -i victron
```

Look for `Victron scanner active`. If data stays stale, re-check MAC/key, Instant Readout on the device, dongle range, and that Bluetooth is not rfkill-blocked.

---

14. Install PCCS as a systemd service and start it on boot:

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

Enable and start the service:

```bash
sudo systemctl link "$PCCS_HOME.service"
sudo systemctl daemon-reload
sudo systemctl enable pccs4.service
sudo systemctl start pccs4.service
sudo systemctl status pccs4.service
```

Allow the PCCS service user to run live Wi‑Fi scans and connections (see [Scripts](#scripts) — `install-networkmanager-perms.sh`):

```bash
sudo usermod -aG netdev "$USERNAME"
sudo "$PCCS_HOME/scripts/install-networkmanager-perms.sh"
sudo systemctl restart pccs4.service
```

On the **System** tab **Wi‑Fi** tile: tap a network to select it (highlight + password form if needed), then press **Connect** — tapping the network name alone does not connect.

Verify:

```bash
sudo systemctl status pccs4
journalctl -u pccs4.service -f
```

Open the UI at `http://10.10.10.1` (or via Cloudflare Tunnel once configured). Diagnostics and overrides are on the **System** tab.

Log files (if Samba enabled): `\\10.10.10.1\pccs4\logs`.

---

### Scripts

Utility scripts live in `scripts/`. Export `PCCS_HOME` before running them (see the env block at the start of [Software installation](#software-installation--configuration)).

| Script | Run as | When |
|--------|--------|------|
| `setup-screen.sh` | `$USERNAME` (not sudo) | Once per remote touchscreen (install step 12) |
| `install-dnsmasq-screens.sh` | `sudo` | After editing `config/dnsmasq/50-pccs-screens.conf` |
| `install-networkmanager-perms.sh` | `sudo` | Install step 14; re-run after `config/polkit/` changes |

#### `setup-screen.sh`

Prepares a remote touchscreen Pi so PCCS can wake, dim, and blank it over SSH when the linked reed opens or closes.

1. Creates `~/.ssh/pccs_screen` (if missing) and adds a `Host` block to `~/.ssh/config`
2. Runs `ssh-copy-id` — prompts for the **touchscreen SSH password** once
3. Installs passwordless sudo on the touchscreen for framebuffer blanking (`/sys/class/graphics/fb0/blank`) — prompts for **touchscreen sudo** once

Safe to re-run: existing keys and SSH config entries are skipped; blank sudoers is overwritten with the same rule, not duplicated.

```bash
export SCREEN_USER=pi      # SSH user on the touchscreen ([screens] username)
export SCREEN_HOST=10.10.10.10
"$PCCS_HOME/scripts/setup-screen.sh"
```

| Option / env | Effect |
|--------------|--------|
| `--ssh-only` | SSH keys only |
| `--blank-only` | Blank permissions only (SSH must already work) |
| `SKIP_BLANK=1` | Skip framebuffer blank setup |
| `BLANK_PATH=...` | Override blank sysfs path (default `/sys/class/graphics/fb0/blank`) |
| `SCREEN_ALIAS=...` | SSH config alias (default `kitchen-screen`) |

Repeat with each panel's `SCREEN_USER` and `SCREEN_HOST`. The script verifies passwordless SSH at the end (same flags PCCS uses).

#### `install-dnsmasq-screens.sh`

Applies fixed DHCP reservations for touchscreen Pis from the repo into the running dnsmasq instance.

1. Copies `config/dnsmasq/50-pccs-screens.conf` → `/etc/dnsmasq.d/50-pccs-screens.conf`
2. Removes duplicate `dhcp-host=` lines for the same MAC from `/etc/dnsmasq.conf`
3. Clears stale leases in `/var/lib/misc/dnsmasq.leases` so reserved MACs pick up their fixed IP immediately
4. Validates config and restarts dnsmasq

Edit `dhcp-host=` lines in the repo file first (MAC must match `dnsmasq.leases`; IP must match `[screens] host` in `config/pccs.conf`), then:

```bash
sudo "$PCCS_HOME/scripts/install-dnsmasq-screens.sh"
```

Renew DHCP on each touchscreen after running (reboot or replug Ethernet).

#### `install-networkmanager-perms.sh`

Installs the polkit rule that lets the PCCS service user control Wi‑Fi without a desktop login session.

1. Copies `config/polkit/50-pccs-networkmanager.rules` → `/etc/polkit-1/rules.d/50-pccs-networkmanager.rules`
2. Grants `network-control`, Wi‑Fi scan, and connection-profile changes to members of the `netdev` group

The service user must also be in `netdev` (`sudo usermod -aG netdev "$USERNAME"`). Without this, the System tab Wi‑Fi tile may show cached scan results and connect attempts fail with *Not authorized to control networking*.

```bash
sudo usermod -aG netdev "$USERNAME"
sudo "$PCCS_HOME/scripts/install-networkmanager-perms.sh"
sudo systemctl restart pccs4.service
```

Safe to re-run on every update when `config/polkit/` changes.

---

### Updating the PCCS

1. SSH into the Pi and copy the latest project files into `$PCCS_HOME`.

   **Samba** (step 7): from your PC, copy updated files into `\\10.10.10.1\pccs4`. You can overwrite the project tree; keep local files such as `config/pccs.conf`, `logs/`, and anything else you have customised.

   **Git** (optional — only if you installed from the step 9 clone and still have a `.git` folder):

```bash
export USERNAME=pi
export PCCS_HOME=/home/$USERNAME/pccs4

cd "$PCCS_HOME"
git pull
```

   Then refresh Python dependencies:

```bash
cd "$PCCS_HOME"
source venv/bin/activate
pip install -r requirements.txt

chmod +x venv/bin/victron
```

2. Update the Pi OS at the same time:

```bash
sudo apt update && sudo apt upgrade -y
```

3. Re-run installers if their config changed (see [Scripts](#scripts)):

```bash
sudo "$PCCS_HOME/scripts/install-networkmanager-perms.sh"   # config/polkit/
sudo "$PCCS_HOME/scripts/install-dnsmasq-screens.sh"        # config/dnsmasq/
```

4. Reboot if asked, otherwise restart PCCS:

```bash
sudo systemctl restart pccs4
```

---

### Run application manually

For debugging — stop the background service first:

```bash
sudo systemctl stop pccs4.service
```

Run in the foreground:

```bash
export USERNAME=pi
export PCCS_HOME=/home/$USERNAME/pccs4

cd "$PCCS_HOME"
source venv/bin/activate
python app.py
```

Press Ctrl+C when done, then restore the service:

```bash
sudo systemctl start pccs4.service
```

---

## Other setup

### NAT/Routing/Internet

**Before you begin:**

- Connect WAN (iPhone tether or Wi‑Fi). For iPhone USB hotspot: `nmcli device connect eth1` (or the name from `nmcli device status`).
- Tether interfaces commonly appear on the UI as `eth1` (not `usb0`) when wired LAN is already `eth0`. WAN is either Wi‑Fi (`wlan0`) or the iPhone tether.

1. Configure the LAN static IP (eth0) and upstream route priorities:

```bash
nmcli connection show
nmcli connection modify "netplan-eth0" ipv4.addresses 10.10.10.1/24
nmcli connection modify "netplan-eth0" ipv4.method manual
nmcli connection modify "netplan-eth0" connection.autoconnect yes
nmcli connection down "netplan-eth0"
nmcli connection up "netplan-eth0"
```

Identify the tether interface (after plugging in the iPhone with hotspot on):

```bash
nmcli device status
ip -br link show | grep -E 'eth|usb'
```

Prefer iPhone USB hotspot (`eth1`) over Wi‑Fi (`wlan0`):

```bash
nmcli connection show

nmcli connection modify "eth1" ipv4.route-metric 50 autoconnect yes
nmcli connection modify "netplan-wlan0-YourSSID" ipv4.route-metric 200 autoconnect yes

nmcli connection down "eth1" || true
nmcli connection up "eth1" || true
nmcli connection down "netplan-wlan0-YourSSID" || true
nmcli connection up "netplan-wlan0-YourSSID" || true
```

Check with `ip route show` — the default route should prefer the tether (lower metric) when both WANs are up.

2. Configure dnsmasq as a DHCP server on the internal LAN only (installed in step 6). It must **only** listen on eth0.

Create `/etc/dnsmasq.conf` (edit `except-interface` to match your upstream interfaces — typically `wlan0` and tether `eth1`):

```ini
interface=eth0
bind-interfaces
except-interface=wlan0
except-interface=eth1

dhcp-range=10.10.10.50,10.10.10.200,255.255.255.0,12h

dhcp-option=3,10.10.10.1
dhcp-option=6,10.10.10.1
```

Enable and start:

```bash
sudo systemctl enable --now dnsmasq
```

**Touchscreen DHCP reservations:** PCCS expects fixed IPs for remote screens (see install step 12). Edit `dhcp-host=` lines in `config/dnsmasq/50-pccs-screens.conf` then run `install-dnsmasq-screens.sh` (see [Scripts](#scripts)).

Confirm with `ip -4 addr show` on the panel and `cat /var/lib/misc/dnsmasq.leases` on the PCCS Pi — kitchen should show `10.10.10.10`.

If a panel keeps the wrong address, confirm it uses **DHCP** on eth0 (not a static IP in NetworkManager) and that the Ethernet MAC in `dhcp-host=` matches `dnsmasq.leases`.

3. Enable IP forwarding:

```bash
echo 'net.ipv4.ip_forward=1' | sudo tee /etc/sysctl.d/99-pccs-nat.conf
sudo sysctl -p /etc/sysctl.d/99-pccs-nat.conf
```

4. Install iptables and set up NAT/masquerading. WAN interfaces are `wlan0` (Wi‑Fi) and tether (usually `eth1` when eth0 is LAN).

Apply rules (adjust `eth1` if your tether has a different name):

```bash
sudo apt install -y iptables iptables-persistent
sudo iptables -t nat -F
sudo iptables -t filter -F
sudo iptables -t nat -A POSTROUTING -o wlan0 -j MASQUERADE
sudo iptables -t nat -A POSTROUTING -o eth1 -j MASQUERADE
sudo iptables -A FORWARD -i eth0 -o wlan0 -j ACCEPT
sudo iptables -A FORWARD -i eth0 -o eth1 -j ACCEPT
sudo iptables -A FORWARD -i wlan0 -o eth0 -m state --state RELATED,ESTABLISHED -j ACCEPT
sudo iptables -A FORWARD -i eth1 -o eth0 -m state --state RELATED,ESTABLISHED -j ACCEPT
sudo netfilter-persistent save
```

Verify:

```bash
sudo iptables -t nat -L -v -n
ip route
```

Restart services:

```bash
sudo systemctl restart NetworkManager dnsmasq
sudo reboot
```

After reboot, test from a device on the eth0 LAN:

```bash
ping 8.8.8.8
ping google.com
```

Confirm DHCP is only on the wired LAN:

```bash
sudo ss -tulnnp | grep dnsmasq
ip addr show
ip route show
```

---

### UniFi OS Server

1. Go to the [UniFi software download page](https://ui.com/download/software/unifi-os-server), right-click the Linux arm64 download link, and copy the URL.

2. Download the installer:

```bash
wget -O unifiosinstaller [PASTE THE COPIED LINK HERE]
```

3. Install Podman:

```bash
sudo apt update
sudo apt install podman
```

4. Run the installer:

```bash
sudo chmod +x unifiosinstaller
sudo ./unifiosinstaller
```

5. Grant server admin rights:

```bash
export USERNAME=pi
sudo usermod -aG uosserver "$USERNAME"
```

Access the UI at `https://10.10.10.1:11443`.

---

## License

Licensed under the [MIT License](LICENSE).
