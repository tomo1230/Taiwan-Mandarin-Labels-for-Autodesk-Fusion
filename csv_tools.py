"""Round-trip the translation tables through CSV so they can be edited in a spreadsheet.

    python csv_tools.py export      zh_tw.json / zh_tw_long.json -> .csv
    python csv_tools.py import      the .csv files -> back into the .json
    python csv_tools.py check       report symbols the translation dropped

The CSV carries two columns, english and traditional. Only the second is meant
to be edited: english is the lookup key the add-in matches against Fusion's own
labels, so changing it silently disables that entry.

Files are written UTF-8 with a BOM, which is what Excel needs to open Chinese
text correctly. LibreOffice and Google Sheets accept it too.

Importing rewrites the .json files, keeping a timestamped copy of the previous
contents in backups/. An import that would drop more than 10% of the entries is
refused, since that usually means a truncated or filtered CSV; pass --force to
go ahead anyway.
"""

import csv
import json
import os
import re
import sys
from collections import Counter

import tablebackup

HERE = os.path.dirname(os.path.abspath(__file__))

PAIRS = [
    ("zh_tw.json", "zh_tw.csv", "names"),
    ("zh_tw_long.json", "zh_tw_long.csv", "descriptions"),
]

FIELDS = ["english", "traditional"]

# Set by --force: allows an import that would delete most of the table.
FORCE = False


def _p(name):
    return os.path.join(HERE, name)


def export():
    for js, cs, label in PAIRS:
        if not os.path.exists(_p(js)):
            print(f"  skip {js} (not found -- run build_dict.py first)")
            continue
        with open(_p(js), encoding="utf-8") as f:
            table = json.load(f)
        # newline="" is required or csv doubles up line endings on Windows
        with open(_p(cs), "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS, quoting=csv.QUOTE_ALL)
            w.writeheader()
            for en in sorted(table):
                w.writerow({"english": en, "traditional": table[en]})
        print(f"  {cs:18} {len(table):6} rows  [{label}]")


def _read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return {}, ["file is empty"]

    missing = [c for c in FIELDS if c not in rows[0]]
    if missing:
        return {}, [f"missing column(s): {', '.join(missing)}"]

    table = {}
    problems = []
    for i, row in enumerate(rows, start=2):        # row 1 is the header
        en = (row.get("english") or "").strip()
        zh = (row.get("traditional") or "").strip()
        if not en:
            problems.append(f"row {i}: empty english, skipped")
            continue
        if not zh:
            problems.append(f"row {i}: empty traditional for {en!r}, skipped")
            continue
        if en in table:
            problems.append(f"row {i}: duplicate english {en!r}, later value wins")
        table[en] = zh
    return table, problems


def do_import():
    if FORCE:
        print("  (--force: the deletion guard is off)")
    for js, cs, label in PAIRS:
        if not os.path.exists(_p(cs)):
            print(f"  skip {cs} (not found -- run export first)")
            continue

        table, problems = _read_csv(_p(cs))
        if not table:
            print(f"  {cs}: nothing usable -- {'; '.join(problems)}")
            continue

        before = {}
        if os.path.exists(_p(js)):
            with open(_p(js), encoding="utf-8") as f:
                before = json.load(f)

        added = [k for k in table if k not in before]
        removed = [k for k in before if k not in table]
        changed = [k for k in table if k in before and before[k] != table[k]]

        # A CSV that lost most of its rows -- a partial export, a spreadsheet
        # saved with a filter applied -- would silently gut the table. Refuse
        # rather than write it, unless the caller says they meant it.
        if before and len(removed) > len(before) * 0.10 and not FORCE:
            pct = len(removed) * 100 // len(before)
            print(f"  {js}: REFUSED -- {len(removed)} of {len(before)} entries "
                  f"({pct}%) would be removed.")
            print(f"      {cs} has {len(table)} rows; the table has {len(before)}.")
            print("      Re-export, or pass --force if the deletion is intended.")
            continue

        saved = tablebackup.backup(_p(js))
        with open(_p(js), "w", encoding="utf-8") as f:
            json.dump(table, f, ensure_ascii=False, indent=0, sort_keys=True)

        print(f"  {js:18} {len(table):6} entries  [{label}]")
        print(f"      changed {len(changed)}, added {len(added)}, removed {len(removed)}")
        for k in changed[:5]:
            print(f"        {k!r}: {before[k]!r} -> {table[k]!r}")
        if len(changed) > 5:
            print(f"        ... and {len(changed) - 5} more")
        for p in problems[:10]:
            print(f"      ! {p}")
        if len(problems) > 10:
            print(f"      ! ... and {len(problems) - 10} more")
        if saved:
            print(f"      backup: "
                  f"{os.path.join(tablebackup.BACKUP_DIR, os.path.basename(saved))}")


# --- consistency checks --------------------------------------------------
#
# The english side carries control characters the UI depends on, and a
# translation that drops them changes behaviour rather than wording. These
# compare the two sides and report whatever went missing.

_TAG = re.compile(r"</?([a-zA-Z][a-zA-Z0-9]*)\b[^>]*>")
_HREF = re.compile(r'href\s*=\s*"([^"]*)"', re.I)
_PLACEHOLDER = re.compile(r"%[0-9A-Za-z_]+%|\{\d+\}")


def _tags(s):
    return Counter(m.lower() for m in _TAG.findall(s))


CHECKS = [
    # (label, why it matters, test)
    ("placeholder", "a value is substituted here at runtime",
     lambda e, z: set(_PLACEHOLDER.findall(e)) != set(_PLACEHOLDER.findall(z))),
    ("html tag", "markup has to survive or the layout breaks",
     lambda e, z: _tags(e) != _tags(z)),
    ("link target", "href must stay identical or the help link dies",
     lambda e, z: set(_HREF.findall(e)) != set(_HREF.findall(z))),
    ("accelerator", "& marks the Alt shortcut; dropping it removes the shortcut",
     lambda e, z: ("&" in e) != ("&" in z)),
    ("ellipsis", "... tells the user a dialog will open",
     lambda e, z: e.rstrip().endswith("...") != z.rstrip().endswith("...")),
    ("stray space", "leading or trailing space in the translation",
     lambda e, z: z != z.strip()),
]


def check():
    total = 0
    for js, _cs, label in PAIRS:
        if not os.path.exists(_p(js)):
            print("  skip %s (not found)" % js)
            continue
        with open(_p(js), encoding="utf-8") as f:
            table = json.load(f)

        print("\n  %s  [%s]  %d entries" % (js, label, len(table)))
        clean = True
        for name, why, differs in CHECKS:
            hits = [(e, z) for e, z in table.items() if differs(e, z)]
            if not hits:
                continue
            clean = False
            total += len(hits)
            print("    %s: %d -- %s" % (name, len(hits), why))
            for e, z in hits[:3]:
                print("        %r" % e[:58])
                print("     -> %r" % z[:58])
            if len(hits) > 3:
                print("        ... and %d more" % (len(hits) - 3))
        if clean:
            print("    nothing to report")

    print("\n  %d entries differ between the two sides." % total)
    print("  Some of that comes from Autodesk's own Simplified Chinese data, so")
    print("  a count above zero is normal. Compare before and after your edits")
    print("  rather than aiming for zero.")


def main():
    global FORCE
    FORCE = "--force" in sys.argv
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "export":
        print("Exporting to CSV:")
        export()
        print("\nEdit the 'traditional' column, then: python csv_tools.py import")
    elif cmd == "import":
        print("Importing from CSV:")
        do_import()
        print("\nRestart Fusion to pick up the new tables.")
    elif cmd == "check":
        print("Checking the tables:")
        check()
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
