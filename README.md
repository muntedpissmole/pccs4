# PCCS4 Demo

A self-contained demo of the Pissmole Camper Control System — runs on Ubuntu Server with no Raspberry Pi hardware. Lights, reed switches, Sonos, battery/solar, water, and GPS are simulated so you can explore the full web UI (lighting, scenes, home dashboard, system tab) as if the camper were real.

Reed switches open and close on their own every few hours; the Sonos tile plays through a built-in trance playlist with artwork.

## Install

```bash
git clone -b demo git@github.com:muntedpissmole/pccs4.git ~/pccs-demo
cd ~/pccs-demo
chmod +x scripts/install-demo.sh
sudo ./scripts/install-demo.sh
```

Open `http://<server-ip>/` in a browser.

The installer sets up the Python venv, `requirements-demo.txt`, a `pccs-demo` systemd service, and nginx on port 80 (with WebSocket support for the live UI).

## After install

```bash
sudo systemctl status pccs-demo
sudo journalctl -u pccs-demo -f
```

After pulling code changes: `sudo systemctl restart pccs-demo`