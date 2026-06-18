#!/usr/bin/env python3
"""Generate demo indie/alternative playlist artwork and download CC-licensed tracks from ccMixter."""

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

# UI metadata shows well-known alternative artists; audio is CC-licensed indie from ccMixter.
TRACKS = [
    {
        "title": "Strong",
        "artist": "London Grammar",
        "album": "If You Wait",
        "duration_seconds": 243,
        "file_name": "01-london-grammar-strong.mp3",
        "art_name": "01-london-grammar-strong.svg",
        "url": "https://ccmixter.org/content/widardizier/widardizier_-_Alone_1.mp3",
        "colors": ("#1c1917", "#78716c", "#d6d3d1"),
    },
    {
        "title": "Wasting My Young Years",
        "artist": "London Grammar",
        "album": "If You Wait",
        "duration_seconds": 245,
        "file_name": "02-london-grammar-wasting-my-young-years.mp3",
        "art_name": "02-london-grammar-wasting-my-young-years.svg",
        "url": "https://ccmixter.org/content/jaspertine/jaspertine_-_Wearing_the_Self_like_a_Hat_11.mp3",
        "colors": ("#0f172a", "#475569", "#cbd5e1"),
    },
    {
        "title": "Cosmic Love",
        "artist": "Florence + The Machine",
        "album": "Lungs",
        "duration_seconds": 256,
        "file_name": "03-florence-cosmic-love.mp3",
        "art_name": "03-florence-cosmic-love.svg",
        "url": "https://ccmixter.org/content/PorchCat/PorchCat_-_Dreams_in_the_Sacred_Cube_1.mp3",
        "colors": ("#3b0764", "#a855f7", "#f5d0fe"),
    },
    {
        "title": "Breezeblocks",
        "artist": "Alt-J",
        "album": "An Awesome Wave",
        "duration_seconds": 227,
        "file_name": "04-alt-j-breezeblocks.mp3",
        "art_name": "04-alt-j-breezeblocks.svg",
        "url": "https://ccmixter.org/content/Mo71/Mo71_-_Switching_Accounts.mp3",
        "colors": ("#14532d", "#22c55e", "#bbf7d0"),
    },
    {
        "title": "Intro",
        "artist": "The xx",
        "album": "xx",
        "duration_seconds": 127,
        "file_name": "05-the-xx-intro.mp3",
        "art_name": "05-the-xx-intro.svg",
        "url": "https://ccmixter.org/content/Javolenus/Javolenus_-_Weather_Or_Not.mp3",
        "colors": ("#111827", "#374151", "#9ca3af"),
    },
    {
        "title": "Holocene",
        "artist": "Bon Iver",
        "album": "Bon Iver",
        "duration_seconds": 337,
        "file_name": "06-bon-iver-holocene.mp3",
        "art_name": "06-bon-iver-holocene.svg",
        "url": "https://ccmixter.org/content/KungFuFrijters/KungFuFrijters_-_Hawkesbury-Dyarubbin_(Dream_Mix).mp3",
        "colors": ("#1e3a8a", "#60a5fa", "#dbeafe"),
    },
    {
        "title": "Youth",
        "artist": "Daughter",
        "album": "If You Leave",
        "duration_seconds": 283,
        "file_name": "07-daughter-youth.mp3",
        "art_name": "07-daughter-youth.svg",
        "url": "https://ccmixter.org/content/scomber/scomber_-_A_Coffee_and_Cigarette.mp3",
        "colors": ("#431407", "#ea580c", "#fed7aa"),
    },
    {
        "title": "The Mother We Share",
        "artist": "CHVRCHES",
        "album": "The Bones of What You Believe",
        "duration_seconds": 192,
        "file_name": "08-chvrches-the-mother-we-share.mp3",
        "art_name": "08-chvrches-the-mother-we-share.svg",
        "url": "https://ccmixter.org/content/airtone/airtone_-_reCycles.mp3",
        "colors": ("#831843", "#ec4899", "#fbcfe8"),
    },
    {
        "title": "Do I Wanna Know?",
        "artist": "Arctic Monkeys",
        "album": "AM",
        "duration_seconds": 272,
        "file_name": "09-arctic-monkeys-do-i-wanna-know.mp3",
        "art_name": "09-arctic-monkeys-do-i-wanna-know.svg",
        "url": "https://ccmixter.org/content/JeffSpeed68/JeffSpeed68_-_Peacemaker.mp3",
        "colors": ("#171717", "#525252", "#d4d4d4"),
    },
    {
        "title": "Stubborn Love",
        "artist": "The Lumineers",
        "album": "The Lumineers",
        "duration_seconds": 279,
        "file_name": "10-lumineers-stubborn-love.mp3",
        "art_name": "10-lumineers-stubborn-love.svg",
        "url": "https://ccmixter.org/content/SpinOpel/SpinOpel_-_Hot_spring.mp3",
        "colors": ("#422006", "#d97706", "#fde68a"),
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
            <path d="M40 380 C140 300, 220 420, 320 340 S 472 300, 472 300"/>
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
            "license": "Creative Commons (ccMixter demo audio)",
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