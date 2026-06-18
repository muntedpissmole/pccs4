# PCCS4 Demo

A self-contained demo of the Pissmole Camper Control System — runs on Linux. Lights, reed switches, Sonos, battery/solar, water, and GPS are simulated so you can explore the full web UI (lighting, scenes, home dashboard, system tab).

Reed switches open and close on their own every few hours; the Sonos tile plays through a built-in playlist.

## Install

```bash
git clone -b demo git@github.com:muntedpissmole/pccs4.git ~/pccs-demo
cd ~/pccs-demo
chmod +x scripts/install-demo.sh
sudo ./scripts/install-demo.sh
```

Open `http://<server-ip>:5000/` in a browser.

The installer sets up the Python venv, `requirements-demo.txt`, and a `pccs-demo` systemd service listening on port 5000.

## After install

```bash
sudo systemctl status pccs-demo
sudo journalctl -u pccs-demo -f
```
To make sure there's no errors.

After pulling code changes: `sudo systemctl restart pccs-demo`

## Uninstall

Removes the systemd service, Python venv, logs, firewall rule, and any legacy nginx site from older installs. The repo directory is kept — delete it manually if you no longer need it.

```bash
cd ~/pccs-demo
chmod +x scripts/uninstall-demo.sh
sudo ./scripts/uninstall-demo.sh
```
