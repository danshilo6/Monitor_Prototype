#!/usr/bin/env python3
"""
Manual integration test for ServerManager.upload_eintzofia_config().

Run from the project root:
    python scripts/test_upload_eintzofia_config.py
    python scripts/test_upload_eintzofia_config.py --server http://127.0.0.1:5001
    python scripts/test_upload_eintzofia_config.py --dry-run
"""

import argparse
import io
import json
import logging
import os
import re
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests
from monitor.core.os_manager import OSManager
from monitor.core.server_manager import ServerManager
from monitor.services.config_service import ConfigService


logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)-8s %(name)s  %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("test_upload_eintzofia_config")

_IP_PATTERN = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")


def _section(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print("─" * 60)


def _describe_temp_dir(temp_dir: Path) -> None:
    _section("EinTzofia temp directory contents")

    if not temp_dir.exists():
        print(f"  [MISSING] {temp_dir}")
        return

    print(f"  Path: {temp_dir}")
    found_any = False

    for entry in sorted(temp_dir.iterdir()):
        if entry.is_dir() and _IP_PATTERN.match(entry.name):
            files = list(entry.iterdir())
            print(f"  [DIR]  {entry.name}  ({len(files)} file(s))")
            found_any = True
        elif entry.name == "configfile.json":
            print(f"  [FILE] configfile.json  ({entry.stat().st_size} bytes)")
            found_any = True

    if not found_any:
        print("  (no IP folders or configfile.json found — nothing would be uploaded)")


_IMAGE_EXTENSIONS = [".jpeg", ".jpg", ".png"]


def _build_payloads(temp_dir: Path) -> tuple[list[tuple[str, bytes]], list[str]]:
    """
    Zip specific image files per camera folder and configfile.json, read into memory.
    For each IP folder, only includes:
      - {ip}.jpeg/jpg/png  (main image)
      - {ip}_regions.jpeg/jpg/png  (regions image)
    Returns (file_payloads, temp_zip_paths) — caller must clean up temp_zip_paths.
    """
    file_payloads: list[tuple[str, bytes]] = []
    temp_zip_paths: list[str] = []

    # Each entry: (zip_filename, list of (arcname, filepath))
    items: list[tuple[str, list[tuple[str, Path]]]] = []

    for entry in temp_dir.iterdir():
        if not (entry.is_dir() and _IP_PATTERN.match(entry.name)):
            continue
        ip = entry.name
        specific_files: list[tuple[str, Path]] = []
        for ext in _IMAGE_EXTENSIONS:
            candidate = entry / f"{ip}{ext}"
            if candidate.is_file():
                specific_files.append((f"{ip}/{candidate.name}", candidate))
                break
        for ext in _IMAGE_EXTENSIONS:
            candidate = entry / f"{ip}_regions{ext}"
            if candidate.is_file():
                specific_files.append((f"{ip}/{candidate.name}", candidate))
                break
        if specific_files:
            items.append((f"{ip}.zip", specific_files))

    configfile = temp_dir / "configfile.json"
    if configfile.exists():
        items.append(("configfile.zip", [("configfile.json", configfile)]))

    for zip_name, file_entries in items:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
            zip_path = tmp.name
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for arcname, source_path in file_entries:
                zf.write(source_path, arcname)

        temp_zip_paths.append(zip_path)
        with open(zip_path, "rb") as f:
            file_payloads.append((zip_name, f.read()))

    return file_payloads, temp_zip_paths


def _raw_upload(endpoint: str, device_id: str, location: str, temp_dir: Path) -> None:
    """
    Re-send the same multipart POST independently and print the full server response.
    This lets us inspect the JSON body (snapshot_id, files_saved, etc.) even when
    upload_eintzofia_config() only returns True/False.
    """
    _section("Raw server response (independent request)")

    if not temp_dir.exists():
        print("  Temp dir missing — cannot send request.")
        return

    file_payloads, temp_zip_paths = _build_payloads(temp_dir)
    try:
        if not file_payloads:
            print("  Nothing to upload.")
            return

        files = [
            ("file", (name, io.BytesIO(data), "application/zip"))
            for name, data in file_payloads
        ]
        post_data = {"device_id": device_id, "location": location}

        print(f"\n  POST {endpoint}")
        print(f"  device_id : {device_id[:20]}...")
        print(f"  location  : {location!r}")
        print(f"  files     : {[name for name, _ in file_payloads]}")

        response = requests.post(endpoint, files=files, data=post_data, timeout=60)

        print(f"\n  HTTP {response.status_code}")
        try:
            body = response.json()
            print(json.dumps(body, indent=2))
        except ValueError:
            print(response.text)

    finally:
        for path in temp_zip_paths:
            try:
                os.unlink(path)
            except OSError:
                pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Integration test for upload_eintzofia_config()")
    parser.add_argument("--server", help="Override server URL  e.g. http://127.0.0.1:5001")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Describe what would be uploaded without sending any request",
    )
    args = parser.parse_args()

    # ── Initialise ────────────────────────────────────────────────────────────
    _section("Initialising")
    config_service = ConfigService()
    os_manager = OSManager(config_service)

    if args.server:
        config_service.set("general", "server_url", args.server)
        print(f"  Server URL overridden: {args.server}")

    server_url = config_service.get("general", "server_url", "")
    location   = config_service.get("general", "location_name", "unknown")
    device_id  = os_manager.generate_device_id()
    temp_dir   = Path(os_manager.get_temp_dir_path())

    print(f"  server_url : {server_url}")
    print(f"  location   : {location!r}")
    print(f"  device_id  : {device_id[:20]}...")
    print(f"  temp_dir   : {temp_dir}")

    # ── What's in the temp dir ────────────────────────────────────────────────
    _describe_temp_dir(temp_dir)

    if args.dry_run:
        print("\n  [dry-run] Stopping here — no request sent.")
        return

    # ── Call via ServerManager ────────────────────────────────────────────────
    _section("Calling server_manager.upload_eintzofia_config()")
    server_manager = ServerManager(config_service, os_manager)
    result = server_manager.upload_eintzofia_config()
    print(f"\n  Return value: {result}")

    if not result:
        # Could be cooldown — check explicitly so the log is clear
        cooldown_url = f"{server_url}/check_config_upload_cooldown"
        try:
            cr = requests.get(cooldown_url, params={"device_id": device_id}, timeout=10)
            if cr.status_code == 200:
                body = cr.json()
                if body.get("on_cooldown"):
                    print(f"  [on cooldown] retry_after_hours={body.get('retry_after_hours')}")
        except Exception:
            pass

    # ── Raw request for full response inspection ──────────────────────────────
    endpoint = f"{server_url}/upload_site_config"
    _raw_upload(endpoint, device_id, location, temp_dir)

    _section("Summary")
    status = "SUCCESS" if result else "FAILED"
    print(f"  upload_eintzofia_config() → {result}  [{status}]\n")


if __name__ == "__main__":
    main()
