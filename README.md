# PCCS4 Demo

A self-contained demo of the Pissmole Camper Control System — runs on Linux. Lights, reed switches, Sonos, battery/solar, water, and GPS are simulated so you can explore the full web UI (lighting, scenes, home dashboard, system tab).

Reed switches open and close on their own every few hours; the Sonos tile plays through a built-in indie/alternative playlist.

## Install

```bash
git clone -b demo https://github.com/muntedpissmole/pccs4.git ~/pccs-demo
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

## Update

Use the update script (handles `git pull`, dependency refresh, and config safely):

```bash
cd ~/pccs-demo
chmod +x scripts/update-demo.sh
sudo ./scripts/update-demo.sh
```

**Do not edit `config/pccs.conf` on the server.** The installer writes machine-specific settings (port, `debug = false`, etc.) to `config/pccs.local.conf`, which git ignores. If you need custom settings, edit `pccs.local.conf` and restart the service.

If you previously hit a `git pull` error about `config/pccs.conf`, run `update-demo.sh` once — it resets that file and pulls cleanly.

## Uninstall

Removes the systemd service, Python venv, logs, and firewall rule. The repo directory is kept — delete it manually if you no longer need it.

```bash
cd ~/pccs-demo
chmod +x scripts/uninstall-demo.sh
sudo ./scripts/uninstall-demo.sh
```