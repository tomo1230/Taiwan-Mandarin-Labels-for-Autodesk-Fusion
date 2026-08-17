"""Relabels ribbon commands, tabs and panels in Taiwan Mandarin (zh-TW).

The target is Taiwan Mandarin written in Traditional Chinese -- the language
Fusion would label "Chinese (Traditional)". It is not Taiwanese Hokkien, and
not the Traditional Chinese used in Hong Kong, which differs in vocabulary.


The translation tables (zh_tw.json, zh_tw_long.json) are produced by
build_dict.py. Their keys are the English source strings, so Fusion's user
language must be set to English -- with a Japanese UI, cd.name returns
Japanese and nothing matches.

Every replacement is recorded so stop() can put the original strings back.
"""

import json
import os
import re
import traceback

import adsk.core

HERE = os.path.dirname(os.path.abspath(__file__))
DICT_PATH = os.path.join(HERE, "zh_tw.json")            # display names (short)
DICT_LONG_PATH = os.path.join(HERE, "zh_tw_long.json")  # tooltips / descriptions
LOG_PATH = os.path.join(HERE, "last_run.log")

# Show the result in a dialog on startup. Set to False once this is routine.
SHOW_SUMMARY = True

# --- Paths confirmed unusable on the real product (2704.1.53) ---------------
# Both look available in core.d.ts but are rejected by the implementation.
# The code is kept and disabled by default in case a later release opens it up.
#
# DropDownControl: id can be read, but reading name raises RuntimeError
#   (InternalValidationError : nuInputControl) and text does not exist at all.
#   There are 570 of them under the panels, none reachable.
TRY_DROPDOWN = False
#
# Workspace: all 52 writes to tooltip/tooltipDescription failed with
#   "The tooltip text displayed for the native workspaces could not be modified"
#   Non-native workspaces (created by add-ins) may still accept writes, so
#   isNative is excluded even when this is turned on.
TRY_WORKSPACE = False

_app = None
_ui = None

# For restoring: [(object, attribute name, original value), ...]
_originals = []


def _log(lines):
    try:
        with open(LOG_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except Exception:
        pass


# Tooltips at runtime are several StringTable entries joined with <br>.
# The pattern is captured so the separators survive the split.
_BR_RE = re.compile(r"(<br\s*/?>)", re.IGNORECASE)


def _norm(s):
    """Lookup key that absorbs trailing punctuation and whitespace drift.

    The running product reports 'displays here' while StringTable stores
    'displays here.' -- the trailing period is inconsistent.
    """
    return s.strip().rstrip(".:：。").strip()


def _build_index(tips):
    """Normalised key -> translation. Fallback when an exact match fails."""
    idx = {}
    for k, v in tips.items():
        idx.setdefault(_norm(k), v)
    return idx


def _translate_rich(text, tips, idx):
    """Translate each <br>-delimited fragment. Returns None if nothing matched."""
    if text in tips:
        return tips[text]

    parts = _BR_RE.split(text)
    out = []
    hit = False
    for part in parts:
        if not part or _BR_RE.fullmatch(part) or not part.strip():
            out.append(part)  # keep separators and whitespace as they are
            continue
        v = tips.get(part.strip())
        if v is None:
            v = idx.get(_norm(part))
        if v is None:
            out.append(part)
        else:
            out.append(v)
            hit = True
    return "".join(out) if hit else None


def _swap_rich(obj, attr, tips, idx):
    """For tooltips and descriptions: translate fragment by fragment."""
    try:
        current = getattr(obj, attr)
    except Exception:
        return False
    if not current or not current.strip():
        return False
    replacement = _translate_rich(current, tips, idx)
    if not replacement or replacement == current:
        return False
    try:
        setattr(obj, attr, replacement)
    except Exception:
        return False
    _originals.append((obj, attr, current))
    return True


def _swap(obj, attr, table):
    """Replace obj.attr when the table has it, recording the original."""
    try:
        current = getattr(obj, attr)
    except Exception:
        return False
    if not current:
        return False
    replacement = table.get(current.strip())
    if not replacement or replacement == current:
        return False
    try:
        setattr(obj, attr, replacement)
    except Exception:
        # Some definitions refuse writes. Skip them individually.
        return False
    _originals.append((obj, attr, current))
    return True


# Drop-downs can nest, so cap the depth. Real menus are 2-3 deep; the cap also
# guarantees termination if controls ever contains itself.
MAX_DEPTH = 8


def _walk_controls(controls, table, counter, depth=0):
    """Walk ToolbarControls recursively, relabelling every DropDownControl.

    counter is a single-element list so the count is shared with the caller.
    """
    if controls is None or depth > MAX_DEPTH:
        return
    try:
        n = controls.count
    except Exception:
        return

    for i in range(n):
        try:
            ctrl = controls.item(i)
        except Exception:
            continue
        if ctrl is None:
            continue

        # cast returns None for CommandControl, SeparatorControl and friends
        try:
            dd = adsk.core.DropDownControl.cast(ctrl)
        except Exception:
            dd = None
        if dd is None:
            continue

        # Both name and text drive the display, so keep them in step
        hit = False
        if _swap(dd, "text", table):
            hit = True
        if _swap(dd, "name", table):
            hit = True
        if hit:
            counter[0] += 1

        try:
            child = dd.controls
        except Exception:
            child = None
        _walk_controls(child, table, counter, depth + 1)


def _apply(ui, table, tips, log):
    n_cmd = n_tip = n_tab = n_panel = n_ws = 0
    n_drop = [0]
    idx = _build_index(tips)

    defs = ui.commandDefinitions
    for i in range(defs.count):
        try:
            cd = defs.item(i)
        except Exception:
            continue
        if cd is None:
            continue
        if _swap(cd, "name", table):
            n_cmd += 1
        if _swap_rich(cd, "tooltip", tips, idx):
            n_tip += 1

    for ws in ui.workspaces:
        # Workspace.name is read-only, and native workspaces also refuse
        # writes to the description.
        if TRY_WORKSPACE:
            try:
                native = ws.isNative
            except Exception:
                native = True
            if not native:
                hit = False
                if _swap_rich(ws, "tooltip", tips, idx):
                    hit = True
                if _swap_rich(ws, "tooltipDescription", tips, idx):
                    hit = True
                if hit:
                    n_ws += 1

        try:
            tabs = ws.toolbarTabs
        except Exception:
            continue
        for tab in tabs:
            if _swap(tab, "name", table):
                n_tab += 1
            try:
                panels = tab.toolbarPanels
            except Exception:
                continue
            for panel in panels:
                if _swap(panel, "name", table):
                    n_panel += 1
                if TRY_DROPDOWN:
                    try:
                        _walk_controls(panel.controls, table, n_drop)
                    except Exception:
                        pass

    # Toolbars that live outside any workspace: QAT, navigation bar, banners
    if TRY_DROPDOWN:
        try:
            toolbars = ui.toolbars
            for i in range(toolbars.count):
                tb = toolbars.item(i)
                if tb is None:
                    continue
                try:
                    _walk_controls(tb.controls, table, n_drop)
                except Exception:
                    continue
        except Exception:
            pass

    log.append(f"Command names : {n_cmd}")
    log.append(f"Tooltips      : {n_tip}")
    log.append(f"Tab names     : {n_tab}")
    log.append(f"Panel names   : {n_panel}")
    if TRY_DROPDOWN:
        log.append(f"Drop-downs    : {n_drop[0]}")
    else:
        log.append("Drop-downs    : disabled (name unreadable; confirmed on product)")
    if TRY_WORKSPACE:
        log.append(f"Workspaces    : {n_ws} (non-native only)")
    else:
        log.append("Workspaces    : disabled (native writes refused; confirmed on product)")
    log.append(f"Total replaced: {len(_originals)}")
    return n_cmd, n_tip, n_tab, n_panel, n_drop[0], n_ws


def run(context):
    global _app, _ui
    log = []
    try:
        _app = adsk.core.Application.get()
        _ui = _app.userInterface

        missing = [p for p in (DICT_PATH, DICT_LONG_PATH) if not os.path.exists(p)]
        if missing:
            _ui.messageBox(
                "Translation table not found.\n\n"
                "Run build_dict.py outside Fusion first.\n\n"
                + "\n".join(missing),
                "FusionZhTW",
            )
            return

        with open(DICT_PATH, encoding="utf-8") as f:
            table = json.load(f)
        with open(DICT_LONG_PATH, encoding="utf-8") as f:
            tips = json.load(f)
        log.append(f"Tables: {len(table)} names / {len(tips)} descriptions")

        n_cmd, n_tip, n_tab, n_panel, n_drop, n_ws = _apply(_ui, table, tips, log)
        _log(log)

        if SHOW_SUMMARY:
            _ui.messageBox(
                "Taiwan Mandarin (zh-TW) labels applied.\n"
                "Traditional Chinese, Taiwan vocabulary.\n\n"
                f"Command names : {n_cmd}\n"
                f"Tooltips      : {n_tip}\n"
                f"Tab names     : {n_tab}\n"
                f"Panel names   : {n_panel}\n\n"
                "Drop-downs, workspaces, dialog contents and the\n"
                "browser tree cannot be changed by Fusion's design.",
                "FusionZhTW",
            )

    except Exception:
        log.append(traceback.format_exc())
        _log(log)
        if _ui:
            _ui.messageBox(
                "FusionZhTW failed to start:\n\n" + traceback.format_exc(),
                "FusionZhTW",
            )


def stop(context):
    """Put the original labels back when the add-in is stopped."""
    try:
        for obj, attr, value in reversed(_originals):
            try:
                setattr(obj, attr, value)
            except Exception:
                pass
        _originals.clear()
    except Exception:
        if _ui:
            _ui.messageBox(
                "FusionZhTW failed to stop:\n\n" + traceback.format_exc(),
                "FusionZhTW",
            )
