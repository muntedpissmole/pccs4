#!/usr/bin/env python3
"""Download real album artwork and CC-licensed demo audio for the Sonos playlist."""

from __future__ import annotations

import json
import re
import subprocess
import textwrap
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART_DIR = ROOT / "static" / "demo" / "sonos-art"
MUSIC_DIR = ROOT / "static" / "demo" / "music"
PLAYLIST_PATH = ROOT / "config" / "demo_playlist.json"
USER_AGENT = "PCCS4-Demo/1.0 (Ubuntu; demo playlist setup)"

# UI metadata shows well-known alternative artists; audio is CC-licensed indie from ccMixter.
TRACKS = [
    {
        "title": "Strong",
        "artist": "London Grammar",
        "album": "If You Wait",
        "duration_seconds": 243,
        "file_name": "01-london-grammar-strong.mp3",
        "art_name": "01-london-grammar-strong.jpg",
        "url": "https://ccmixter.org/content/widardizier/widardizier_-_Alone_1.mp3",
        "colors": ("#1c1917", "#78716c", "#d6d3d1"),
    },
    {
        "title": "Wasting My Young Years",
        "artist": "London Grammar",
        "album": "If You Wait",
        "duration_seconds": 245,
        "file_name": "02-london-grammar-wasting-my-young-years.mp3",
        "art_name": "02-london-grammar-wasting-my-young-years.jpg",
        "url": "https://ccmixter.org/content/jaspertine/jaspertine_-_Wearing_the_Self_like_a_Hat_11.mp3",
        "colors": ("#0f172a", "#475569", "#cbd5e1"),
    },
    {
        "title": "Cosmic Love",
        "artist": "Florence + The Machine",
        "album": "Lungs",
        "duration_seconds": 256,
        "file_name": "03-florence-cosmic-love.mp3",
        "art_name": "03-florence-cosmic-love.jpg",
        "url": "https://ccmixter.org/content/PorchCat/PorchCat_-_Dreams_in_the_Sacred_Cube_1.mp3",
        "colors": ("#3b0764", "#a855f7", "#f5d0fe"),
    },
    {
        "title": "Breezeblocks",
        "artist": "Alt-J",
        "album": "An Awesome Wave",
        "duration_seconds": 227,
        "file_name": "04-alt-j-breezeblocks.mp3",
        "art_name": "04-alt-j-breezeblocks.jpg",
        "url": "https://ccmixter.org/content/Mo71/Mo71_-_Switching_Accounts.mp3",
        "colors": ("#14532d", "#22c55e", "#bbf7d0"),
    },
    {
        "title": "Intro",
        "artist": "The xx",
        "album": "xx",
        "duration_seconds": 127,
        "file_name": "05-the-xx-intro.mp3",
        "art_name": "05-the-xx-intro.jpg",
        "url": "https://ccmixter.org/content/Javolenus/Javolenus_-_Weather_Or_Not.mp3",
        "colors": ("#111827", "#374151", "#9ca3af"),
    },
    {
        "title": "Holocene",
        "artist": "Bon Iver",
        "album": "Bon Iver",
        "duration_seconds": 337,
        "file_name": "06-bon-iver-holocene.mp3",
        "art_name": "06-bon-iver-holocene.jpg",
        "url": "https://ccmixter.org/content/KungFuFrijters/KungFuFrijters_-_Hawkesbury-Dyarubbin_(Dream_Mix).mp3",
        "colors": ("#1e3a8a", "#60a5fa", "#dbeafe"),
    },
    {
        "title": "Youth",
        "artist": "Daughter",
        "album": "If You Leave",
        "duration_seconds": 283,
        "file_name": "07-daughter-youth.mp3",
        "art_name": "07-daughter-youth.jpg",
        "url": "https://ccmixter.org/content/scomber/scomber_-_A_Coffee_and_Cigarette.mp3",
        "colors": ("#431407", "#ea580c", "#fed7aa"),
    },
    {
        "title": "The Mother We Share",
        "artist": "CHVRCHES",
        "album": "The Bones of What You Believe",
        "duration_seconds": 192,
        "file_name": "08-chvrches-the-mother-we-share.mp3",
        "art_name": "08-chvrches-the-mother-we-share.jpg",
        "url": "https://ccmixter.org/content/airtone/airtone_-_reCycles.mp3",
        "colors": ("#831843", "#ec4899", "#fbcfe8"),
    },
    {
        "title": "Do I Wanna Know?",
        "artist": "Arctic Monkeys",
        "album": "AM",
        "duration_seconds": 272,
        "file_name": "09-arctic-monkeys-do-i-wanna-know.mp3",
        "art_name": "09-arctic-monkeys-do-i-wanna-know.jpg",
        "url": "https://ccmixter.org/content/JeffSpeed68/JeffSpeed68_-_Peacemaker.mp3",
        "colors": ("#171717", "#525252", "#d4d4d4"),
    },
    {
        "title": "Stubborn Love",
        "artist": "The Lumineers",
        "album": "The Lumineers",
        "duration_seconds": 279,
        "file_name": "10-lumineers-stubborn-love.mp3",
        "art_name": "10-lumineers-stubborn-love.jpg",
        "url": "https://ccmixter.org/content/SpinOpel/SpinOpel_-_Hot_spring.mp3",
        "colors": ("#422006", "#d97706", "#fde68a"),
    },
]


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _itunes_search(term: str, entity: str, limit: int = 5) -> list[dict]:
    query = urllib.parse.urlencode({"term": term, "entity": entity, "limit": str(limit)})
    request = urllib.request.Request(
        f"https://itunes.apple.com/search?{query}",
        headers={"User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload.get("results", [])


def _pick_album_result(results: list[dict], artist: str, album: str) -> dict | None:
    artist_key = _normalize(artist)
    album_key = _normalize(album)
    for result in results:
        if artist_key in _normalize(result.get("artistName", "")) and album_key in _normalize(
            result.get("collectionName", "")
        ):
            return result
    for result in results:
        if artist_key in _normalize(result.get("artistName", "")):
            return result
    return results[0] if results else None


def _artwork_url(result: dict) -> str | None:
    url = result.get("artworkUrl100") or result.get("artworkUrl60")
    if not url:
        return None
    return (
        url.replace("100x100bb", "600x600bb")
        .replace("60x60bb", "600x600bb")
        .replace("100x100", "600x600")
        .replace("60x60", "600x600")
    )


def fetch_album_art(track: dict) -> str | None:
    artist = track["artist"]
    album = track["album"]
    title = track["title"]

    searches = [
        ("album", f"{artist} {album}"),
        ("album", album),
        ("song", f"{title} {artist}"),
    ]
    for entity, term in searches:
        try:
            results = _itunes_search(term, entity)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            continue
        match = _pick_album_result(results, artist, album)
        url = _artwork_url(match) if match else None
        if url:
            return url
    return None


def download_artwork(track: dict) -> bool:
    dest = ART_DIR / track["art_name"]
    if dest.exists() and dest.stat().st_size > 20_000:
        return True

    url = fetch_album_art(track)
    if not url:
        write_fallback_artwork(track)
        return False

    try:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read()
        if len(data) < 10_000:
            raise ValueError("artwork too small")
        dest.write_bytes(data)
        return True
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        write_fallback_artwork(track)
        return False


def _xml_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def write_fallback_artwork(track: dict) -> None:
    """Gradient SVG placeholder when iTunes artwork is unavailable."""
    bg, accent, glow = track["colors"]
    title = _xml_escape(track["title"])
    artist = _xml_escape(track["artist"])
    fallback = track["art_name"].rsplit(".", 1)[0] + ".svg"
    svg = textwrap.dedent(
        f"""\
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" role="img" aria-label="{title}">
          <defs>
            <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="{bg}"/>
              <stop offset="55%" stop-color="{accent}"/>
              <stop offset="100%" stop-color="{glow}"/>
            </linearGradient>
          </defs>
          <rect width="512" height="512" fill="url(#bg)"/>
          <text x="256" y="392" text-anchor="middle" fill="#f8fafc" font-family="system-ui,sans-serif"
                font-size="30" font-weight="700">{title}</text>
          <text x="256" y="430" text-anchor="middle" fill="#e2e8f0" font-family="system-ui,sans-serif"
                font-size="22" opacity="0.9">{artist}</text>
        </svg>
        """
    )
    (ART_DIR / fallback).write_text(svg, encoding="utf-8")
    track["art_name"] = fallback


def download_track(track: dict) -> bool:
    dest = MUSIC_DIR / track["file_name"]
    if dest.exists() and dest.stat().st_size > 100_000:
        return True
    try:
        subprocess.run(
            [
                "curl", "-fsSL",
                "-A", USER_AGENT,
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
        ok = download_artwork(track)
        status = "ok" if ok else "fallback"
        print(f"art  → {track['art_name']} ({status})")

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