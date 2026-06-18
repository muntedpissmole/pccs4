# PCCS4 Demo

Self-contained demo branch for running PCCS on **Ubuntu Server** without Raspberry Pi hardware.

## What is simulated

| Component | Demo behaviour |
|-----------|----------------|
| **Time / GPS** | Host system clock + configured demo coordinates |
| **Lights & relays** | In-memory Arduino/GPIO — sliders, scenes, and reeds all work |
| **Reed switches** | Simulated; one reed opens/closes at random every 2–6 hours |
| **Sonos** | Local playlist player — edit `config/demo_playlist.json` |
| **Victron / power** | Slowly varying battery and solar numbers |
| **Water & temps** | Simulated tank level and DS18B20 readings |
| **Screens** | Brightness tracked in memory (no SSH to remote Pis) |

## Install on Ubuntu Server (one-off)

Clone the demo branch, then run the installer **once**. It creates the Python venv, installs a `pccs-demo` systemd service (enabled + started), and configures nginx on port 80 with WebSocket support for Socket.IO.

```bash
git clone -b demo git@github.com:muntedpissmole/pccs4.git ~/pccs-demo
cd ~/pccs-demo
chmod +x scripts/install-demo.sh
sudo ./scripts/install-demo.sh
```

Open `http://<server-ip>/` in a browser (nginx proxies to the app on `127.0.0.1:5000`).

Optional environment overrides:

| Variable | Default | Purpose |
|----------|---------|---------|
| `INSTALL_DIR` | repo root | Where `app.py` lives |
| `SERVER_NAME` | `_` | nginx `server_name` |
| `SERVICE_USER` | `$SUDO_USER` | Unix user for the service |

After code changes:

```bash
cd ~/pccs-demo && git pull
sudo systemctl restart pccs-demo
```

Service management:

```bash
sudo systemctl status pccs-demo
sudo journalctl -u pccs-demo -f
```

## Playlist (Sonos tile)

The demo ships with **10 Creative Commons trance tracks** from [ccMixter](https://ccmixter.org), each with generated artwork in `static/demo/sonos-art/`.

To refresh tracks and art:

```bash
~/pccs-demo/venv/bin/python ~/pccs-demo/scripts/setup-demo-playlist.py
sudo systemctl restart pccs-demo
```

Edit `config/demo_playlist.json` to swap tracks or point `album_art` at your own images under `static/`. Restart the service after changes.

The `file` field points at downloaded MP3s under `static/demo/music/`. The Sonos tile uses title, artist, artwork, progress bar, and transport controls.

## Configuration

Demo settings live in `config/pccs.conf` under `[demo]`:

- `enabled` — must be `true` for simulation (default on this branch)
- `latitude` / `longitude` / `timezone` / `suburb` — location for sun times and GPS tile
- `reed_toggle_min_hours` / `reed_toggle_max_hours` — random reed event interval
- `sonos_autoplay` — start playback on launch

The installer sets `host = 127.0.0.1` and `debug = false` in `pccs.conf`.

## Git branch

This folder is a git worktree on the `demo` branch:

```bash
git branch        # * demo
git push -u origin demo
```

Production hardware runs from `main` in `~/pccs4`.