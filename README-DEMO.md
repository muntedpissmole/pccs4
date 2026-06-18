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

## Quick start (Ubuntu)

```bash
cd ~/pccs-demo
chmod +x scripts/run-demo.sh scripts/setup-demo-playlist.py
./scripts/setup-demo-playlist.py   # optional: refresh CC trance tracks + artwork
./scripts/run-demo.sh
```

Open `http://<server-ip>:5000` in a browser.

### Running the app

Use a **virtualenv** — `scripts/run-demo.sh` creates one, activates it, installs `requirements-demo.txt`, then runs `python app.py` inside that venv.

Equivalent manual steps:

```bash
cd ~/pccs-demo
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-demo.txt
python app.py
```

Either way, the important part is that `python app.py` runs **inside** the activated venv, not system Python.

## Playlist (Sonos tile)

The demo ships with **10 Creative Commons trance tracks** from [ccMixter](https://ccmixter.org), each with generated artwork in `static/demo/sonos-art/`.

To refresh tracks and art:

```bash
./scripts/setup-demo-playlist.py
```

Edit `config/demo_playlist.json` to swap tracks or point `album_art` at your own images under `static/`. Restart the app after changes.

The `file` field points at downloaded MP3s under `static/demo/music/` when available; local audio playback can be wired up later. The Sonos tile already uses title, artist, artwork, progress bar, and transport controls.

## Configuration

Demo settings live in `config/pccs.conf` under `[demo]`:

- `enabled` — must be `true` for simulation (default on this branch)
- `latitude` / `longitude` / `timezone` / `suburb` — location for sun times and GPS tile
- `reed_toggle_min_hours` / `reed_toggle_max_hours` — random reed event interval
- `sonos_autoplay` — start playback on launch

## Git branch

This folder is a git worktree on the `demo` branch:

```bash
git branch        # * demo
git push -u origin demo
```

Production hardware runs from `main` in `~/pccs4`.