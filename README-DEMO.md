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
chmod +x bin/run-demo.sh
./bin/run-demo.sh
```

Open `http://<server-ip>:5000` in a browser.

## Playlist (Sonos tile)

Edit `config/demo_playlist.json` and restart the app:

```json
{
  "speaker_name": "Kitchen",
  "volume": 35,
  "tracks": [
    {
      "title": "Your Song",
      "artist": "Artist Name",
      "album": "Album",
      "duration_seconds": 240,
      "file": "/path/to/song.mp3"
    }
  ]
}
```

The `file` field is reserved for future local audio playback. For now, tracks drive the Sonos tile UI (title, artist, progress bar, transport controls).

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