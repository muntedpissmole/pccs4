#!/usr/bin/env python3
"""Generate demo trance playlist artwork and download CC-licensed tracks from ccMixter."""

from __future__ import annotations

import json
import re
import subprocess
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART_DIR = ROOT / "static" / "demo" / "sonos-art"
MUSIC_DIR = ROOT / "static" / "demo" / "music"
PLAYLIST_PATH = ROOT / "config" / "demo_playlist.json"

# Creative Commons trance / psytrance tracks from ccMixter (demo use).
TRACKS = [
    {
        "title": "Oasis of Pulse",
        "artist": "Zenboy1955",
        "album": "ccMixter Trance",
        "duration_seconds": 263,
        "file_name": "01-oasis-of-pulse.mp3",
        "art_name": "01-oasis-of-pulse.svg",
        "url": "https://ccmixter.org/content/Zenboy1955/Zenboy1955_-_Oasis_of_Pulse.mp3",
        "colors": ("#12002e", "#7c3aed", "#22d3ee"),
    },
    {
        "title": "Moon Circuit",
        "artist": "Karstenholymoly",
        "album": "ccMixter Trance",
        "duration_seconds": 181,
        "file_name": "02-moon-circuit.mp3",
        "art_name": "02-moon-circuit.svg",
        "url": "https://ccmixter.org/content/Karstenholymoly/Karstenholymoly_-_Moon_Circuit.mp3",
        "colors": ("#0f172a", "#6366f1", "#a5b4fc"),
    },
    {
        "title": "clear4",
        "artist": "softmartin",
        "album": "ccMixter Trance",
        "duration_seconds": 175,
        "file_name": "03-clear4.mp3",
        "art_name": "03-clear4.svg",
        "url": "https://ccmixter.org/content/softmartin/softmartin_-_clear4.mp3",
        "colors": ("#042f2e", "#14b8a6", "#99f6e4"),
    },
    {
        "title": "The Point is the Chaos",
        "artist": "Reiswerk",
        "album": "ccMixter Trance",
        "duration_seconds": 291,
        "file_name": "04-the-point-is-the-chaos.mp3",
        "art_name": "04-the-point-is-the-chaos.svg",
        "url": "https://ccmixter.org/content/Reiswerk/Reiswerk_-_The_Point_is_the_Chaos.mp3",
        "colors": ("#3b0764", "#c026d3", "#f0abfc"),
    },
    {
        "title": "Uathach",
        "artist": "Dimensional Pulse",
        "album": "ccMixter Trance",
        "duration_seconds": 420,
        "file_name": "05-uathach.mp3",
        "art_name": "05-uathach.svg",
        "url": "https://ccmixter.org/content/Dimensional_Pulse/Dimensional_Pulse_-_Uathach.mp3",
        "colors": ("#1e1b4b", "#4f46e5", "#818cf8"),
    },
    {
        "title": "Conciousness Always Finds A Way",
        "artist": "Dimensional Pulse",
        "album": "ccMixter Trance",
        "duration_seconds": 468,
        "file_name": "06-consciousness-always-finds-a-way.mp3",
        "art_name": "06-consciousness-always-finds-a-way.svg",
        "url": "https://ccmixter.org/content/Dimensional_Pulse/Dimensional_Pulse_-_Conciousness_Always_Finds_A_Way.mp3",
        "colors": ("#052e16", "#22c55e", "#86efac"),
    },
    {
        "title": "Commuting Through the Oort Cloud",
        "artist": "Zenboy1955",
        "album": "ccMixter Trance",
        "duration_seconds": 414,
        "file_name": "07-commuting-through-the-oort-cloud.mp3",
        "art_name": "07-commuting-through-the-oort-cloud.svg",
        "url": "https://ccmixter.org/content/Zenboy1955/Zenboy1955_-_Commuting_Through_the_Oort_Cloud_1.mp3",
        "colors": ("#0c1445", "#2563eb", "#93c5fd"),
    },
    {
        "title": "Holdmeback (140 Trance Mix)",
        "artist": "DJDecay",
        "album": "ccMixter Trance",
        "duration_seconds": 494,
        "file_name": "08-holdmeback-140-trance-mix.mp3",
        "art_name": "08-holdmeback-140-trance-mix.svg",
        "url": "https://ccmixter.org/content/DJDecay/DJDecay_-_Holdmeback_(140_Trance_Mix)_1.mp3",
        "colors": ("#431407", "#f97316", "#fdba74"),
    },
    {
        "title": "Obscurantism",
        "artist": "Dimensional Pulse",
        "album": "ccMixter Trance",
        "duration_seconds": 540,
        "file_name": "09-obscurantism.mp3",
        "art_name": "09-obscurantism.svg",
        "url": "https://ccmixter.org/content/Dimensional_Pulse/Dimensional_Pulse_-_Obscurantism_1.mp3",
        "colors": ("#450a0a", "#ef4444", "#fca5a5"),
    },
    {
        "title": "140 BPM Trance Dance (Stem Mix)",
        "artist": "DJDecay",
        "album": "ccMixter Trance",
        "duration_seconds": 494,
        "file_name": "10-trance-dance-stem-mix.mp3",
        "art_name": "10-trance-dance-stem-mix.svg",
        "url": "https://ccmixter.org/content/DJDecay/DJDecay_-_140_BPM_Trance_Dance_Stems_CopyLeft_1.mp3",
        "colors": ("#172554", "#3b82f6", "#bfdbfe"),
    },
]


def _xml_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def write_artwork(track: dict) -> None:
    bg, accent, glow = track["colors"]
    title = _xml_escape(track["title"])
    artist = _xml_escape(track["artist"])
    svg = textwrap.dedent(
        f"""\
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" role="img" aria-label="{title}">
          <defs>
            <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="{bg}"/>
              <stop offset="55%" stop-color="{accent}"/>
              <stop offset="100%" stop-color="{glow}"/>
            </linearGradient>
            <radialGradient id="orb" cx="50%" cy="35%" r="55%">
              <stop offset="0%" stop-color="{glow}" stop-opacity="0.95"/>
              <stop offset="100%" stop-color="{accent}" stop-opacity="0"/>
            </radialGradient>
          </defs>
          <rect width="512" height="512" fill="url(#bg)"/>
          <circle cx="256" cy="190" r="150" fill="url(#orb)"/>
          <g opacity="0.35" stroke="{glow}" stroke-width="2" fill="none">
            <path d="M40 380 C140 300, 220 420, 320 340 S472 300, 472 300"/>
            <path d="M30 420 C180 360, 250 460, 360 390 S490 350, 490 350"/>
          </g>
          <text x="256" y="392" text-anchor="middle" fill="#f8fafc" font-family="system-ui,sans-serif"
                font-size="30" font-weight="700">{title}</text>
          <text x="256" y="430" text-anchor="middle" fill="#e2e8f0" font-family="system-ui,sans-serif"
                font-size="22" opacity="0.9">{artist}</text>
        </svg>
        """
    )
    (ART_DIR / track["art_name"]).write_text(svg, encoding="utf-8")


def download_track(track: dict) -> bool:
    dest = MUSIC_DIR / track["file_name"]
    if dest.exists() and dest.stat().st_size > 100_000:
        return True
    try:
        subprocess.run(
            [
                "curl", "-fsSL",
                "-A", "PCCS4-Demo/1.0 (Ubuntu; demo playlist setup)",
                "-e", "https://ccmixter.org/",
                track["url"], "-o", str(dest),
            ],
            check=True,
            timeout=180,
        )
        return dest.exists()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


def build_playlist(downloaded: dict[str, bool]) -> dict:
    entries = []
    for track in TRACKS:
        file_path = f"static/demo/music/{track['file_name']}" if downloaded.get(track["file_name"]) else None
        entries.append({
            "title": track["title"],
            "artist": track["artist"],
            "album": track["album"],
            "duration_seconds": track["duration_seconds"],
            "album_art": f"/static/demo/sonos-art/{track['art_name']}",
            "file": file_path,
            "source_url": track["url"],
            "license": "Creative Commons (ccMixter)",
        })
    return {
        "speaker_name": "Kitchen",
        "volume": 38,
        "tracks": entries,
    }


def main() -> None:
    ART_DIR.mkdir(parents=True, exist_ok=True)
    MUSIC_DIR.mkdir(parents=True, exist_ok=True)

    for track in TRACKS:
        write_artwork(track)
        print(f"art  → {track['art_name']}")

    downloaded: dict[str, bool] = {}
    for track in TRACKS:
        ok = download_track(track)
        downloaded[track["file_name"]] = ok
        status = "ok" if ok else "skipped"
        print(f"mp3  → {track['file_name']} ({status})")

    playlist = build_playlist(downloaded)
    PLAYLIST_PATH.write_text(json.dumps(playlist, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {PLAYLIST_PATH}")


if __name__ == "__main__":
    main()