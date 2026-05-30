#!/usr/bin/env python3
"""One-shot migration: extract `journey` array from each session JSON into a
sibling `.journey.log` (JSONL), then drop `journey` from the JSON.

Idempotent: sessions with empty/missing journey are skipped. Already-migrated
sessions are re-checked and any residual journey entries are appended to the
log (not duplicated — dedup by (time,event,type,idempotency_key?)).

Usage: python3 migrate-journey-to-log.py [--dry-run]
"""

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path


def atomic_write_json(path: Path, data):
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def event_key(ev):
    idk = ev.get("idempotency_key")
    if idk:
        return ("idk", idk)
    return ("tet", ev.get("time", ""), ev.get("event", ""), ev.get("type", ""))


def migrate_session(session_path: Path, dry_run: bool) -> tuple[int, int]:
    try:
        data = json.loads(session_path.read_text())
    except Exception as e:
        print(f"  SKIP: cannot parse {session_path.name}: {e}", file=sys.stderr)
        return (0, 0)

    journey = data.get("journey")
    if not isinstance(journey, list) or not journey:
        return (0, 0)

    log_path = session_path.with_suffix(".journey.log")

    existing_keys = set()
    if log_path.exists():
        for line in log_path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing_keys.add(event_key(json.loads(line)))
            except Exception:
                continue

    new_lines = []
    for ev in journey:
        if not isinstance(ev, dict):
            continue
        if event_key(ev) in existing_keys:
            continue
        new_lines.append(json.dumps(ev, separators=(",", ":")))

    if dry_run:
        print(f"  {session_path.name}: would append {len(new_lines)} events to {log_path.name}, drop journey field")
        return (len(new_lines), len(journey))

    if new_lines:
        with open(log_path, "a") as f:
            for line in new_lines:
                f.write(line + "\n")

    data.pop("journey", None)
    atomic_write_json(session_path, data)
    print(f"  {session_path.name}: appended {len(new_lines)} events, dropped journey ({len(journey)} total)")
    return (len(new_lines), len(journey))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sessions-dir", default=".adversarial-spec/sessions")
    args = ap.parse_args()

    sessions_dir = Path(args.sessions_dir)
    if not sessions_dir.is_dir():
        print(f"ERROR: {sessions_dir} not found", file=sys.stderr)
        return 2

    total_appended = 0
    total_journey = 0
    for session_path in sorted(sessions_dir.glob("*.json")):
        if session_path.name.endswith(".tmp"):
            continue
        appended, journey_len = migrate_session(session_path, args.dry_run)
        total_appended += appended
        total_journey += journey_len

    mode = "[dry-run] " if args.dry_run else ""
    print(f"{mode}Done. {total_appended} events written across all sessions (source journey total: {total_journey}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
