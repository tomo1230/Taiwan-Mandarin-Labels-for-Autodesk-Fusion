"""Timestamped backups of the translation tables.

Both build_dict.py and csv_tools.py overwrite zh_tw.json / zh_tw_long.json,
and hand-corrected terminology is easy to lose that way -- rebuilding from
StringTable discards every edit. Each write is therefore preceded by a copy
into backups/, named with the time it was taken:

    backups/zh_tw.20260817-214530.json

Old generations are pruned so the folder cannot grow without limit.
"""

import os
import shutil
import time

BACKUP_DIR = "backups"

# How many generations of each table to keep.
KEEP = 20


def backup(path, reason=""):
    """Copy `path` into backups/ before it is overwritten.

    Returns the backup path, or None when there was nothing to back up.
    Never raises: losing a backup must not stop the actual work.
    """
    if not os.path.exists(path):
        return None
    try:
        folder = os.path.join(os.path.dirname(os.path.abspath(path)), BACKUP_DIR)
        os.makedirs(folder, exist_ok=True)

        base = os.path.basename(path)
        stem, ext = os.path.splitext(base)

        # Milliseconds are included so the name sorts chronologically and
        # collisions are effectively impossible. Both matter: _prune orders
        # generations by filename, because shutil.copy2 carries the source
        # file's mtime across and every copy would otherwise look equally old.
        now = time.time()
        stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(now))
        stamp += f"{int((now % 1) * 1000):03d}"
        dest = os.path.join(folder, f"{stem}.{stamp}{ext}")

        # Fallback for the same millisecond. Zero-padded so it still sorts.
        n = 1
        while os.path.exists(dest):
            dest = os.path.join(folder, f"{stem}.{stamp}-{n:02d}{ext}")
            n += 1

        shutil.copy2(path, dest)
        _prune(folder, stem, ext)
        return dest
    except Exception:
        return None


def _age_key(fname, stem, ext):
    """Sort key that puts the newest generation first.

    Plain string order is not enough: within one millisecond the collision
    suffix ("-01") sorts before the unsuffixed name, because "-" precedes "."
    in ASCII, which reverses those few. Splitting the suffix out fixes it.

    Sorting by mtime is not an option -- shutil.copy2 carries the source
    file's mtime onto every copy, so they all look the same age.
    """
    middle = fname[len(stem) + 1:-len(ext)] if ext else fname[len(stem) + 1:]
    head, _, tail = middle.rpartition("-")
    if head and tail.isdigit() and len(tail) <= 2:
        return (head, int(tail))
    return (middle, 0)


def _prune(folder, stem, ext):
    """Keep only the newest KEEP generations of one table."""
    try:
        mine = [
            f for f in os.listdir(folder)
            if f.startswith(stem + ".") and f.endswith(ext)
        ]
        mine.sort(key=lambda f: _age_key(f, stem, ext), reverse=True)
        for old in mine[KEEP:]:
            try:
                os.remove(os.path.join(folder, old))
            except Exception:
                pass
    except Exception:
        pass
