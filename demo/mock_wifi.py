"""Simulated Wi-Fi scanner for demo mode — populates the System tab without nmcli."""

from __future__ import annotations

import math
import time
from typing import Any

_DEMO_NETWORKS = [
    {
        "ssid": "CamperNet",
        "signal": 84,
        "security": "WPA2",
        "band": "5 GHz",
        "saved": True,
        "secured": True,
    },
    {
        "ssid": "Starlink Guest",
        "signal": 67,
        "security": "WPA2",
        "band": "5 GHz",
        "saved": True,
        "secured": True,
    },
    {
        "ssid": "Pissmole",
        "signal": 52,
        "security": "Open",
        "band": "2.4 GHz",
        "saved": False,
        "secured": False,
    },
    {
        "ssid": "Telstra5G",
        "signal": 41,
        "security": "WPA3",
        "band": "5 GHz",
        "saved": False,
        "secured": True,
    },
]

_connected_ssid = "CamperNet"


def _jitter_signal(base: int) -> int:
    t = time.time()
    return max(20, min(100, int(base + math.sin(t / 35.0) * 4)))


def _network_list() -> list[dict[str, Any]]:
    networks = []
    for entry in _DEMO_NETWORKS:
        item = dict(entry)
        item["signal"] = _jitter_signal(item["signal"])
        item["in_use"] = item["ssid"] == _connected_ssid
        networks.append(item)
    networks.sort(key=lambda row: (-int(row.get("in_use", False)), -row["signal"], row["ssid"]))
    return networks


def get_demo_wifi_status() -> dict[str, Any]:
    networks = _network_list()
    active = next((network for network in networks if network.get("in_use")), None)
    return {
        "available": True,
        "iface": "wlan0",
        "state": "connected" if active else "disconnected",
        "connected": active is not None,
        "ssid": active["ssid"] if active else None,
        "signal": active["signal"] if active else None,
        "security": active["security"] if active else None,
        "ip": "10.10.10.1" if active else None,
        "networks": networks,
        "source": "demo",
    }


def scan_demo_wifi_networks() -> dict[str, Any]:
    return {
        "ok": True,
        "networks": _network_list(),
        "source": "demo",
    }


def connect_demo_wifi(ssid: str, password: str | None = None) -> dict[str, Any]:
    global _connected_ssid
    ssid = ssid.strip()
    if not ssid:
        return {"ok": False, "error": "Network name is required", "status": get_demo_wifi_status()}

    known = {network["ssid"] for network in _DEMO_NETWORKS}
    if ssid not in known:
        return {
            "ok": False,
            "error": f"Network “{ssid}” not found — tap Scan and try again",
            "status": get_demo_wifi_status(),
        }

    target = next(network for network in _DEMO_NETWORKS if network["ssid"] == ssid)
    if target.get("secured") and not password:
        return {
            "ok": False,
            "error": "Password required",
            "status": get_demo_wifi_status(),
        }

    _connected_ssid = ssid
    status = get_demo_wifi_status()
    return {
        "ok": True,
        "message": f"Connected to {ssid}",
        "status": status,
    }