#!/usr/bin/env python3
"""

Usage:
    python3 fix_ntfs_prefixes.py --dry-run     # see what would happen
    python3 fix_ntfs_prefixes.py               # do it (auto-detects NTFS libraries)
    python3 fix_ntfs_prefixes.py --compatdata "/mnt/XYZ/Steam/steamapps/compatdata"
Close Steam first.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

NTFS_TYPES = {"ntfs", "ntfs3", "ntfs-3g", "fuseblk"}
SKIP_DIRS = {"Windows", "$RECYCLE.BIN", "System Volume Information", "ProgramData", "Users"}


def steam_running():
    try:
        return subprocess.run(["pgrep", "-x", "steam"], capture_output=True).returncode == 0
    except FileNotFoundError:
        return False


def ntfs_mounts():
    mounts = []
    with open("/proc/mounts") as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 3 and parts[2] in NTFS_TYPES:
                mounts.append(parts[1].replace("\\040", " "))
    return mounts


def find_compatdata_dirs(mount, max_depth=5):
    base = Path(mount)
    base_depth = len(base.parts)
    found = []
    for root, dirs, _ in os.walk(base):
        rootp = Path(root)
        if rootp.name == "compatdata" and rootp.parent.name == "steamapps":
            found.append(rootp)
            dirs[:] = []
            continue
        if len(rootp.parts) - base_depth >= max_depth:
            dirs[:] = []
        else:
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
    return found


def migrate(compatdata, target_root, dry_run, only_foreign):
    uid = os.getuid()
    moved = skipped = failed = 0
    print(f"\nLibrary: {compatdata}")

    for entry in sorted(compatdata.iterdir()):
        if not entry.name.isdigit():
            continue
        if entry.is_symlink():
            print(f"  [skip] {entry.name}: already a symlink")
            skipped += 1
            continue
        if not entry.is_dir():
            continue
        if only_foreign and entry.stat().st_uid == uid:
            print(f"  [skip] {entry.name}: already owned by you")
            skipped += 1
            continue

        dest = target_root / entry.name
        if dest.exists():
            print(f"  [skip] {entry.name}: {dest} already exists")
            skipped += 1
            continue

        if dry_run:
            print(f"  [dry-run] would move {entry.name} -> {dest} and symlink back")
            moved += 1
            continue

        try:
            shutil.move(str(entry), str(dest))
        except Exception as e:
            print(f"  [FAIL] {entry.name}: move failed ({e})")
            # Clean up a partial copy, but only if the original is still there
            if entry.exists() and dest.exists():
                shutil.rmtree(dest, ignore_errors=True)
            failed += 1
            continue

        try:
            entry.symlink_to(dest, target_is_directory=True)
        except OSError as e:
            print(f"  [FAIL] {entry.name}: symlink failed ({e}); moving it back")
            shutil.move(str(dest), str(entry))
            failed += 1
            continue

        print(f"  [ok]   {entry.name} -> {dest}")
        moved += 1

    print(f"  Done: {moved} moved, {skipped} skipped, {failed} failed")
    return failed


def main():
    p = argparse.ArgumentParser(description="Move Proton prefixes off NTFS drives.")
    p.add_argument("--compatdata", action="append", type=Path,
                   help="Path to a steamapps/compatdata folder (repeatable). "
                        "If omitted, NTFS mounts are searched automatically.")
    p.add_argument("--target", type=Path, default=Path.home() / "steam-compatdata",
                   help="Where to store the prefixes (default: ~/steam-compatdata)")
    p.add_argument("--only-foreign", action="store_true",
                   help="Only move prefixes not owned by your user")
    p.add_argument("--dry-run", action="store_true", help="Show actions without changing anything")
    args = p.parse_args()

    if steam_running():
        sys.exit("Steam is running. Close it completely and try again.")

    libraries = args.compatdata or []
    if not libraries:
        print("Searching NTFS mounts for Steam libraries...")
        for mount in ntfs_mounts():
            libraries.extend(find_compatdata_dirs(mount))

    libraries = [l for l in libraries if l.is_dir()]
    if not libraries:
        sys.exit("No compatdata folders found. Pass one with --compatdata.")

    if not args.dry_run:
        args.target.mkdir(parents=True, exist_ok=True)

    total_failed = sum(migrate(lib, args.target, args.dry_run, args.only_foreign) for lib in libraries)
    sys.exit(1 if total_failed else 0)


if __name__ == "__main__":
    main()
