"""Simulated Sonos player — local playlist skeleton (add tracks to config/demo_playlist.json)."""

from __future__ import annotations

import json
import logging
import os
import threading
import time

logger = logging.getLogger("pccs")

_DEFAULT_PLAYLIST = {
    "speaker_name": "Kitchen",
    "volume": 35,
    "tracks": [
        {
            "title": "Demo Track One",
            "artist": "Placeholder Artist",
            "album": "Demo Playlist",
            "duration_seconds": 240,
            "file": None,
        },
        {
            "title": "Demo Track Two",
            "artist": "Placeholder Artist",
            "album": "Demo Playlist",
            "duration_seconds": 195,
            "file": None,
        },
    ],
}


class DemoSonosManager:
    """SonosManager-compatible simulator that plays through a local playlist."""

    def __init__(self, socketio, config):
        self.socketio = socketio
        self.config = config
        self.enabled = True
        self.preferred_name = config.get("sonos", "player_name", fallback=None)
        self.auto_select_first = True
        self.interface_addr = None
        self.poll_interval = config.getint("sonos", "poll_interval", fallback=3)

        self._running = False
        self._poll_thread: threading.Thread | None = None
        self._lock = threading.Lock()

        self._playlist = self._load_playlist()
        speaker = self._playlist.get("speaker_name") or self.preferred_name or "Kitchen"
        self.speakers = {speaker: {"name": speaker}}
        self.current_speaker = speaker
        self._manual_override = False
        self._last_state: dict = {}

        self._track_index = 0
        self._position = 0
        self._playing = config.getboolean("demo", "sonos_autoplay", fallback=True)
        self._volume = int(self._playlist.get("volume", 35))
        self._muted = False
        self._track_started_at = time.time()

        logger.info(f"🎵 Demo Sonos — speaker '{speaker}', {len(self._tracks())} track(s) in playlist")

    def _playlist_path(self) -> str:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base, "config", "demo_playlist.json")

    def _load_playlist(self) -> dict:
        path = self._playlist_path()
        if os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as handle:
                    data = json.load(handle)
                if isinstance(data, dict) and data.get("tracks"):
                    return data
            except Exception as e:
                logger.warning(f"Demo playlist load failed ({path}): {e}")
        return dict(_DEFAULT_PLAYLIST)

    def reload_playlist(self):
        with self._lock:
            self._playlist = self._load_playlist()
            self._track_index = 0
            self._position = 0
            self._track_started_at = time.time()
            logger.info(f"🎵 Demo playlist reloaded — {len(self._tracks())} track(s)")

    def _tracks(self) -> list[dict]:
        return list(self._playlist.get("tracks") or [])

    def _current_track(self) -> dict:
        tracks = self._tracks()
        if not tracks:
            return {
                "title": "Nothing playing",
                "artist": "",
                "album": "",
                "duration_seconds": 0,
                "file": None,
            }
        return tracks[self._track_index % len(tracks)]

    def start(self):
        if self._running:
            return
        self._running = True
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True, name="DemoSonos")
        self._poll_thread.start()
        self._broadcast_speakers()
        self._emit_state()

    def stop(self):
        self._running = False

    def _poll_loop(self):
        while self._running:
            try:
                self._tick_position()
                self._emit_state()
            except Exception as e:
                logger.debug(f"Demo Sonos poll: {e}")
            time.sleep(self.poll_interval)

    def _tick_position(self):
        with self._lock:
            track = self._current_track()
            duration = int(track.get("duration_seconds") or 0)
            if not self._playing or duration <= 0:
                return

            elapsed = int(time.time() - self._track_started_at)
            if elapsed >= duration:
                self._advance_track()
                return
            self._position = elapsed

    def _advance_track(self):
        tracks = self._tracks()
        if not tracks:
            self._playing = False
            self._position = 0
            return
        self._track_index = (self._track_index + 1) % len(tracks)
        self._position = 0
        self._track_started_at = time.time()
        logger.info(f"🎵 Demo Sonos → now playing: {self._current_track().get('title')}")

    def _live_position(self) -> int:
        track = self._current_track()
        duration = int(track.get("duration_seconds") or 0)
        if not self._playing or duration <= 0:
            return self._position
        return min(int(time.time() - self._track_started_at), duration)

    def _build_state(self) -> dict:
        with self._lock:
            track = self._current_track()
            duration = int(track.get("duration_seconds") or 0)
            position = self._live_position()
            return {
                "enabled": True,
                "source": "demo",
                "speaker": self.current_speaker,
                "speakers": list(self.speakers.keys()),
                "track": track.get("title") or "Nothing playing",
                "artist": track.get("artist") or "",
                "album": track.get("album") or "",
                "album_art": track.get("album_art"),
                "is_playing": self._playing,
                "mute": self._muted,
                "volume": self._volume,
                "position": position,
                "elapsed_seconds": position,
                "duration": duration,
                "duration_seconds": duration,
            }

    def _emit_state(self):
        state = self._build_state()
        if state != self._last_state:
            self._last_state = state.copy()
            if self.socketio:
                self.socketio.emit("sonos_update", state)

    def _broadcast_speakers(self):
        if self.socketio:
            self.socketio.emit("sonos_speakers", {
                "speakers": list(self.speakers.keys()),
                "current": self.current_speaker,
                "enabled": True,
            })

    def switch_speaker(self, name: str) -> bool:
        if name not in self.speakers:
            return False
        self.current_speaker = name
        self._manual_override = True
        self._broadcast_speakers()
        return True

    def execute_command(self, data: dict) -> dict:
        cmd = data.get("command")
        value = data.get("value")

        with self._lock:
            if cmd == "playpause":
                self._playing = not self._playing
                if self._playing:
                    self._track_started_at = time.time() - self._position
            elif cmd == "play":
                self._playing = True
                self._track_started_at = time.time() - self._position
            elif cmd == "pause":
                self._playing = False
            elif cmd == "next":
                self._advance_track()
            elif cmd == "previous":
                tracks = self._tracks()
                if tracks:
                    self._track_index = (self._track_index - 1) % len(tracks)
                    self._position = 0
                    self._track_started_at = time.time()
            elif cmd == "volume" and isinstance(value, (int, float)):
                self._volume = max(0, min(100, int(value)))
            elif cmd == "mute":
                if value is None:
                    self._muted = not self._muted
                else:
                    self._muted = bool(value)
            elif cmd == "seek" and value is not None:
                track = self._current_track()
                duration = int(track.get("duration_seconds") or 0)
                if duration > 0:
                    self._position = max(0, min(duration, int(duration * float(value))))
                    self._track_started_at = time.time() - self._position
            else:
                return {"error": f"Unknown command: {cmd}"}

        self._emit_state()
        return {"success": True}

    def request_state(self):
        self._emit_state()

    def get_current_state(self) -> dict:
        return self._build_state()