# NTFS Proton Prefix Fix

Move Steam Proton prefixes (`steamapps/compatdata/<appid>`) off NTFS drives onto your Linux home drive, leaving a symlink behind so Steam still finds them.

## The problem

If your Steam library lives on an NTFS drive, Wine/Proton may complain that the prefix **"is not owned by you"**, or games may fail to launch. NTFS doesn't reliably support Linux file ownership, permissions and symlinks, which Wine prefixes depend on.

## What this does

For each numeric folder in a `compatdata` directory on an NTFS drive, it:

1. Moves the prefix to a folder on your Linux filesystem (default `~/steam-compatdata`).
2. Creates a symlink at the original location pointing to the new one.

Game files stay on the NTFS drive. Only the prefixes move.

## Requirements

- Linux with Python 3.6+
- Steam (closed while running the tool)
- For the GUI only: tkinter
  - Debian/Ubuntu: `sudo apt install python3-tk`
  - Fedora: `sudo dnf install python3-tkinter`
  - Arch: `sudo pacman -S tk`

No other dependencies.

## Installation

```bash
git clone https://github.com/ItsJr420/Fix_NTFS_Prefixes_Linux
cd Fix_NTFS_Prefixes_Linux
```

Or download the ZIP from GitHub and extract it. Keep both `.py` files in the same folder.

## Usage

**Close Steam completely first.** Make sure the target drive has enough free space for your prefixes.

### GUI

```bash
python3 fix_ntfs_prefixes_gui.py
```

1. Click **Auto-detect NTFS libraries** (or **Add folder…** to pick a `steamapps/compatdata` folder manually).
2. Choose where to store the prefixes.
3. Leave **Dry run** ticked and click **Run** to preview.
4. Untick Dry run and click **Run** to do it for real.

### Command line

```bash
python3 fix_ntfs_prefixes.py --dry-run      # preview
python3 fix_ntfs_prefixes.py                # auto-detect NTFS libraries and move prefixes
python3 fix_ntfs_prefixes.py --compatdata "/mnt/games/Steam/steamapps/compatdata"
```

| Option | Description |
|---|---|
| `--compatdata PATH` | A `compatdata` folder to process (repeatable). Skips auto-detection. |
| `--target PATH` | Where prefixes are stored (default `~/steam-compatdata`). |
| `--only-foreign` | Only move prefixes not owned by your user. |
| `--dry-run` | Show what would happen without changing anything. |

## Notes and troubleshooting

- **Back up first** if a prefix holds save games you care about. Moving between filesystems copies then deletes.
- Already-symlinked prefixes and prefixes whose destination already exists are skipped.
- If a move or symlink fails, the script tries to clean up and reports `[FAIL]`; the exit code is 1.
- "No compatdata folders found": pass the path with `--compatdata` (or **Add folder…** in the GUI). Auto-detect only searches a few levels deep in mounted NTFS drives.
- "Steam is running": quit Steam from its tray icon, then check with `pgrep -x steam`.
- To undo a move for one game: delete the symlink and move the folder from the target back to the original path.

## Disclaimer

Provided as-is, with no warranty. Use the dry run first.
