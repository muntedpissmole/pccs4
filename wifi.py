"""Wi-Fi status, scan, and connect via NetworkManager (nmcli)."""

from __future__ import annotations

import re
import shutil
import subprocess
from typing import Any

_WIFI_IFACE: str | None = None

_UNAVAILABLE: dict[str, Any] = {
    "available": False,
    "iface": None,
    "state": "unavailable",
    "connected": False,
    "ssid": None,
    "signal": None,
    "security": None,
    "ip": None,
    "networks": [],
    "error": "NetworkManager (nmcli) not available",
    "source": "unavailable",
}


def _nmcli_available() -> bool:
    return shutil.which("nmcli") is not None


def _run_nmcli(args: list[str], *, timeout: float = 30) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            ["nmcli", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        return 1, "", str(exc)


def _wifi_iface() -> str | None:
    global _WIFI_IFACE

    if _WIFI_IFACE:
        return _WIFI_IFACE

    code, stdout, _ = _run_nmcli(["-t", "-f", "DEVICE,TYPE", "device", "status"], timeout=5)
    if code != 0:
        return None

    for line in stdout.splitlines():
        parts = line.split(":")
        if len(parts) >= 2 and parts[1] == "wifi":
            _WIFI_IFACE = parts[0]
            return _WIFI_IFACE

    return None


def _band_from_channel(channel: str) -> str | None:
    try:
        value = int(channel)
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return None
    return "2.4 GHz" if value < 15 else "5 GHz"


def _format_security(raw: str) -> str:
    value = (raw or "").strip()
    if not value or value == "--":
        return "Open"
    if "WPA3" in value:
        return "WPA3"
    if "WPA2" in value:
        return "WPA2"
    if "WPA1" in value or value == "WPA":
        return "WPA"
    if "WEP" in value:
        return "WEP"
    return value


def _device_state(iface: str) -> str:
    code, stdout, _ = _run_nmcli(["-g", "GENERAL.STATE", "device", "show", iface], timeout=5)
    if code != 0 or not stdout:
        return "unknown"

    match = re.search(r"(\d+)", stdout)
    if not match:
        return "unknown"

    numeric = int(match.group(1))
    if numeric == 100:
        return "connected"
    if numeric in {20, 30, 50, 60, 70, 80, 90}:
        return "connecting"
    if numeric <= 30:
        return "disconnected"
    return "unavailable"


def _device_ip(iface: str) -> str | None:
    code, stdout, _ = _run_nmcli(["-g", "IP4.ADDRESS", "device", "show", iface], timeout=5)
    if code != 0 or not stdout:
        return None

    for line in stdout.splitlines():
        ip = line.split("/", 1)[0].strip()
        if ip:
            return ip
    return None


def _parse_wifi_row(line: str) -> dict[str, Any] | None:
    parts = line.split(":")
    if len(parts) < 5:
        return None

    in_use = parts[0].strip() == "*"
    ssid = ":".join(parts[1:-3]).strip()
    signal_raw = parts[-3].strip()
    security_raw = parts[-2].strip()
    channel_raw = parts[-1].strip()

    if not ssid:
        return None

    try:
        signal = int(signal_raw)
    except ValueError:
        signal = 0

    security = _format_security(security_raw)
    return {
        "ssid": ssid,
        "signal": max(0, min(100, signal)),
        "security": security,
        "in_use": in_use,
        "band": _band_from_channel(channel_raw),
        "secured": security != "Open",
    }


def _parse_wifi_rows(stdout: str) -> list[dict[str, Any]]:
    networks: dict[str, dict[str, Any]] = {}

    for line in stdout.splitlines():
        entry = _parse_wifi_row(line)
        if not entry:
            continue

        ssid = entry["ssid"]
        existing = networks.get(ssid)
        if existing is None:
            networks[ssid] = entry
            continue

        if entry.get("in_use"):
            networks[ssid] = entry
            continue

        if existing.get("in_use"):
            existing["signal"] = max(existing["signal"], entry["signal"])
            continue

        if entry["signal"] > existing["signal"]:
            networks[ssid] = {**entry, "in_use": False}

    rows = list(networks.values())
    rows.sort(key=lambda row: (not row.get("in_use"), -row.get("signal", 0), row.get("ssid", "")))
    return rows


def _saved_ssids() -> set[str]:
    code, stdout, _ = _run_nmcli(["-t", "-f", "NAME,TYPE", "connection", "show"], timeout=5)
    if code != 0:
        return set()

    ssids: set[str] = set()
    for line in stdout.splitlines():
        parts = line.split(":", 1)
        if len(parts) != 2 or parts[1] != "802-11-wireless":
            continue

        profile_code, profile_out, _ = _run_nmcli(
            ["-g", "802-11-wireless.ssid", "connection", "show", parts[0]],
            timeout=5,
        )
        if profile_code == 0 and profile_out.strip():
            ssids.add(profile_out.strip())

    return ssids


def _normalize_scan_warning(stderr: str | None) -> str | None:
    message = (stderr or "").strip()
    if not message:
        return None
    lowered = message.lower()
    if "not authorized" in lowered or "not authorised" in lowered:
        return "Showing cached results — live rescan was not authorized"
    if "insufficient privileges" in lowered:
        return "Showing cached results — NetworkManager denied the scan request"
    return message


def _annotate_saved_profiles(networks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    saved = _saved_ssids()
    annotated: list[dict[str, Any]] = []

    for network in networks:
        row = dict(network)
        row["saved"] = row["ssid"] in saved
        if row["saved"] and row["security"] == "Open" and not row.get("in_use"):
            row["security"] = "Saved"
        annotated.append(row)

    return annotated


def _scan_wifi_networks(iface: str, *, rescan: bool) -> tuple[list[dict[str, Any]], str | None]:
    scan_error = None
    if rescan:
        code, _, stderr = _run_nmcli(["device", "wifi", "rescan", "ifname", iface], timeout=15)
        if code != 0:
            scan_error = _normalize_scan_warning(stderr)

    code, stdout, stderr = _run_nmcli(
        ["-g", "IN-USE,SSID,SIGNAL,SECURITY,CHAN", "device", "wifi", "list", "ifname", iface],
        timeout=20,
    )
    if code != 0:
        message = stderr or "Wi-Fi scan failed"
        return [], message

    networks = _annotate_saved_profiles(_parse_wifi_rows(stdout))
    if not networks and scan_error:
        return [], scan_error
    return networks, scan_error


def get_wifi_status() -> dict[str, Any]:
    if not _nmcli_available():
        return dict(_UNAVAILABLE)

    iface = _wifi_iface()
    if not iface:
        return {
            "available": False,
            "iface": None,
            "state": "unavailable",
            "connected": False,
            "ssid": None,
            "signal": None,
            "security": None,
            "ip": None,
            "networks": [],
            "error": "No Wi-Fi interface found",
            "source": "live",
        }

    state = _device_state(iface)
    networks, scan_error = _scan_wifi_networks(iface, rescan=False)
    active = next((network for network in networks if network.get("in_use")), None)

    return {
        "available": True,
        "iface": iface,
        "state": state,
        "connected": state == "connected" and active is not None,
        "ssid": active["ssid"] if active else None,
        "signal": active["signal"] if active else None,
        "security": active["security"] if active else None,
        "ip": _device_ip(iface) if state == "connected" else None,
        "networks": networks,
        "scan_warning": scan_error,
        "source": "live",
    }


def scan_wifi_networks() -> dict[str, Any]:
    status = get_wifi_status()
    if not status.get("available"):
        return {
            "ok": False,
            "networks": status.get("networks", []),
            "error": status.get("error", "Wi-Fi unavailable"),
            "source": status.get("source", "live"),
        }

    iface = status.get("iface")
    if not iface:
        return {
            "ok": False,
            "networks": [],
            "error": "No Wi-Fi interface found",
            "source": status.get("source", "live"),
        }

    networks, scan_error = _scan_wifi_networks(iface, rescan=True)
    return {
        "ok": bool(networks),
        "networks": networks,
        "warning": scan_error,
        "error": None if networks else (scan_error or "No networks found"),
        "source": "live",
    }


def connect_wifi(ssid: str, password: str | None = None) -> dict[str, Any]:
    ssid = ssid.strip()
    if not ssid:
        return {"ok": False, "error": "Network name is required", "status": get_wifi_status()}

    if not _nmcli_available():
        return {
            "ok": False,
            "error": _UNAVAILABLE["error"],
            "status": dict(_UNAVAILABLE),
        }

    iface = _wifi_iface()
    if not iface:
        return {"ok": False, "error": "No Wi-Fi interface found", "status": get_wifi_status()}

    args = ["device", "wifi", "connect", ssid, "ifname", iface]
    if password:
        args.extend(["password", password])

    code, stdout, stderr = _run_nmcli(args, timeout=45)
    if code != 0:
        message = stderr or stdout or "Connection failed"
        return {"ok": False, "error": message, "status": get_wifi_status()}

    status = get_wifi_status()
    return {
        "ok": True,
        "message": stdout or f"Connected to {ssid}",
        "status": status,
    }