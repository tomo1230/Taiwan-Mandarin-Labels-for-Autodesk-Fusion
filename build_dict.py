"""Build an English -> Taiwan Mandarin (zh-TW) table from Fusion's StringTable.

The target is Taiwan Mandarin in Traditional Chinese script -- not Taiwanese
Hokkien, and not Hong Kong Traditional, whose vocabulary differs.

Each zh-CN XML carries devLabel (the English source) and translation (Simplified
Chinese) on the same line, so those files alone yield English -> Simplified pairs.
Those pass through OpenCC's s2twp profile, which converts Simplified to
Traditional and swaps in Taiwan Mandarin vocabulary (软件 -> 軟體, not 軟件).

Run this outside Fusion. It writes zh_tw.json and zh_tw_long.json alongside itself.
"""

import json
import os
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "zh_tw.json")
OUT_LONG = os.path.join(HERE, "zh_tw_long.json")

PRODUCTION = os.path.join(
    os.environ["LOCALAPPDATA"], "Autodesk", "webdeploy", "production"
)

# The lines to harvest. Attribute order is fixed, but each is captured separately.
LABEL_RE = re.compile(
    r'<label\s+commandName="(?P<key>[^"]*)"\s+devLabel="(?P<en>[^"]*)"\s+'
    r'translation="(?P<zh>[^"]*)"\s*/>'
)

# Table for display names. Long descriptions and error text are cut so the
# table stays focused and false matches stay rare.
MAX_LEN = 40

# Table for tooltips and descriptions, which run longer than any label.
# Nothing here is used as a display name -- FusionZhTW.py keeps the two apart.
MAX_LEN_LONG = 300


def find_stringtable(locale):
    """Locate StringTable/<locale> under the newest webdeploy version folder."""
    candidates = []
    for name in os.listdir(PRODUCTION):
        path = os.path.join(PRODUCTION, name, "StringTable", locale)
        if os.path.isdir(path):
            candidates.append((os.path.getmtime(path), path))
    if not candidates:
        raise SystemExit(f"StringTable/{locale} not found under {PRODUCTION}")
    return max(candidates)[1]


def unescape(s):
    return (
        s.replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#xA;", "\n")
        .replace("&amp;", "&")
    )


def collect(src_dir):
    """Gather en -> Counter(Simplified) twice: once for names, once for descriptions.

    A Counter is used because the same English string can carry several
    translations, which are then resolved by majority.
    """
    short = defaultdict(Counter)
    long_ = defaultdict(Counter)
    files = 0
    for fname in sorted(os.listdir(src_dir)):
        if not fname.lower().endswith(".xml"):
            continue
        files += 1
        with open(os.path.join(src_dir, fname), encoding="utf-8") as f:
            text = f.read()
        for m in LABEL_RE.finditer(text):
            en = unescape(m.group("en")).strip()
            zh = unescape(m.group("zh")).strip()
            if not en or not zh or en == zh:
                continue
            # %1% is filled in at runtime; translating it breaks the string.
            if "%" in en:
                continue
            if len(en) > MAX_LEN_LONG:
                continue
            # Tooltips routinely contain <br> and <b> (verified on the product).
            # Allowing markup here is what makes most of them resolvable.
            long_[en][zh] += 1
            # Display names never carry markup, so keep it out of the short table.
            if len(en) <= MAX_LEN and "\n" not in en and "<" not in en:
                short[en][zh] += 1
    return short, long_, files


def main():
    try:
        from opencc import OpenCC
    except ImportError:
        raise SystemExit(
            "opencc is required:  python -m pip install opencc-python-reimplemented"
        )

    src = find_stringtable("zh-CN")
    print(f"Source: {src}")
    short, long_, files = collect(src)
    print(f"  {files} XML files")

    cc = OpenCC("s2twp")

    def build(pairs):
        table = {}
        ambiguous = 0
        for en, counter in pairs.items():
            if len(counter) > 1:
                ambiguous += 1
            zh_cn = counter.most_common(1)[0][0]  # take the most frequent reading
            table[en] = cc.convert(zh_cn)
        return table, ambiguous

    for path, pairs, label in ((OUT, short, "names"), (OUT_LONG, long_, "descriptions")):
        table, ambiguous = build(pairs)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(table, f, ensure_ascii=False, indent=0, sort_keys=True)
        print(f"Wrote: {os.path.basename(path)} [{label}] {len(table)} entries "
              f"({ambiguous} ambiguous, most frequent reading kept)")

    table, _ = build(short)
    for en in ["Extrude", "Revolve", "Sketch", "Save", "Hole", "Fillet"]:
        if en in table:
            print(f"    {en:10} -> {table[en]}")


if __name__ == "__main__":
    main()
