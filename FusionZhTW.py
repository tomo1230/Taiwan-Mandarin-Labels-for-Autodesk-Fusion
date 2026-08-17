"""Relabels ribbon commands, tabs and panels in Taiwan Mandarin (zh-TW).

The target is Taiwan Mandarin written in Traditional Chinese -- the language
Fusion would label "Chinese (Traditional)". It is not Taiwanese Hokkien, and
not the Traditional Chinese used in Hong Kong, which differs in vocabulary.

The translation tables (zh_tw.json, zh_tw_long.json) are produced by
build_dict.py. Their keys are the English source strings, so Fusion's user
language must be set to English -- with a Japanese UI, cd.name returns
Japanese and nothing matches.

Labels are applied during Fusion's startup only; see run(). Every replacement
is recorded so stop() can put the original strings back.
"""

import json
import os
import re
import time
import traceback

import adsk.core

HERE = os.path.dirname(os.path.abspath(__file__))
DICT_PATH = os.path.join(HERE, "zh_tw.json")            # display names (short)
DICT_LONG_PATH = os.path.join(HERE, "zh_tw_long.json")  # tooltips / descriptions
LOG_PATH = os.path.join(HERE, "last_run.log")

# Show the result in a dialog on startup. Set to False once this is routine.
SHOW_SUMMARY = True

# --- Deliberately not attempted, all verified on the product (2704.1.53) ----
#
# Drop-downs: 570 DropDownControl instances sit under the panels, but
#   reading .name raises RuntimeError (InternalValidationError :
#   nuInputControl) and .text does not exist at all, despite both being
#   declared in core.d.ts. There is nothing to write to.
#
# Workspaces: Workspace.name is read-only as declared, and all 52 writes to
#   tooltip/tooltipDescription were refused with "The tooltip text displayed
#   for the native workspaces could not be modified".
#
# Both were implemented, measured at zero effect, and removed rather than
# left as dead branches. See README, "What blocks the rest".

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


def _apply(ui, table, tips, log):
    """Relabel command definitions, then the tabs and panels of every workspace."""
    n_cmd = n_tip = n_tab = n_panel = 0
    n_ws = 0

    t0 = time.perf_counter()
    idx = _build_index(tips)
    t_idx = time.perf_counter()

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
    t_cmd = time.perf_counter()

    # Reaching toolbarTabs/toolbarPanels instantiates the workspace chrome, so
    # this loop costs far more than the 400-odd strings it replaces. Timed
    # separately to keep that visible.
    for ws in ui.workspaces:
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
    t_ws = time.perf_counter()

    log.append(f"Command names : {n_cmd}")
    log.append(f"Tooltips      : {n_tip}")
    log.append(f"Tab names     : {n_tab}")
    log.append(f"Panel names   : {n_panel}")
    log.append(f"Total replaced: {len(_originals)}")
    log.append("")
    log.append("Timing")
    log.append(f"  build index      : {(t_idx - t0) * 1000:8.0f} ms")
    log.append(f"  {defs.count:5} definitions : {(t_cmd - t_idx) * 1000:8.0f} ms")
    log.append(f"  {n_ws:5} workspaces  : {(t_ws - t_cmd) * 1000:8.0f} ms")
    log.append(f"  apply total      : {(t_ws - t0) * 1000:8.0f} ms")
    return n_cmd, n_tip, n_tab, n_panel


def _language_check(app):
    """Return None when the UI is English, otherwise a message explaining why not.

    The tables are keyed on English source strings, so on any localised UI
    cd.name comes back in that language and nothing matches -- every count
    would be zero. Checking up front turns that silent no-op into a clear
    instruction.

    If the preference cannot be read at all, return None and let the run
    proceed: a missing check should not block a setup that would have worked.
    """
    try:
        prefs = app.preferences.generalPreferences
        current = prefs.userLanguage
    except Exception:
        return None

    if current == adsk.core.UserLanguages.EnglishLanguage:
        return None

    names = {
        adsk.core.UserLanguages.ChinesePRCLanguage: "Chinese (Simplified)",
        adsk.core.UserLanguages.ChineseTaiwanLanguage: "Chinese (Traditional)",
        adsk.core.UserLanguages.CzechLanguage: "Czech",
        adsk.core.UserLanguages.FrenchLanguage: "French",
        adsk.core.UserLanguages.GermanLanguage: "German",
        adsk.core.UserLanguages.HungarianLanguage: "Hungarian",
        adsk.core.UserLanguages.ItalianLanguage: "Italian",
        adsk.core.UserLanguages.JapaneseLanguage: "Japanese",
        adsk.core.UserLanguages.KoreanLanguage: "Korean",
        adsk.core.UserLanguages.PolishLanguage: "Polish",
        adsk.core.UserLanguages.PortugueseBrazilianLanguage: "Portuguese (Brazil)",
        adsk.core.UserLanguages.RussianLanguage: "Russian",
        adsk.core.UserLanguages.SpanishLanguage: "Spanish",
        adsk.core.UserLanguages.TurkishLanguage: "Turkish",
    }
    current_name = names.get(current, f"a non-English language (code {current})")

    return (
        f"FusionZhTW needs the user language set to English.\n\n"
        f"It is currently {current_name}, so nothing has been changed.\n\n"
        "The translation table is keyed on the English labels, so on any "
        "other language there is nothing for it to match.\n\n"
        "To fix:\n"
        "  1. User icon -> Preferences -> General -> User language\n"
        "  2. Choose English\n"
        "  3. Restart Fusion"
    )


def _is_startup(context):
    """True when Fusion is running us as part of its own startup.

    Fusion passes IsApplicationStartup in the run() context. It arrives either
    as a dict or as a JSON string depending on version, so handle both and
    treat anything unrecognised as "not startup" -- the safe direction, since
    that path only warns instead of touching the UI.
    """
    data = context
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            return False
    if isinstance(data, dict):
        return bool(data.get("IsApplicationStartup", False))
    return False


def run(context):
    global _ui
    log = []
    try:
        app = adsk.core.Application.get()
        _ui = app.userInterface

        # Applying mid-session corrupts the workspace switcher: every entry
        # collapses to the same label, leaving it unusable. Verified by
        # bisection -- renaming VisibilityToggleCmd ('Show/Hide') alone is
        # enough to trigger it, and it is not the only definition that can.
        # The switcher is not translatable in the first place (Workspace.name
        # is read-only), so there is nothing to gain by pressing on. Applying
        # only during Fusion's own startup avoids the problem entirely.
        if not _is_startup(context):
            _ui.messageBox(
                "FusionZhTW applies its labels during Fusion startup only.\n\n"
                "Running it mid-session corrupts the workspace switcher, so "
                "nothing has been changed.\n\n"
                "Tick 'Run on Startup' in the Add-Ins dialog, then restart "
                "Fusion.",
                "FusionZhTW",
            )
            _log(["Skipped: not application startup; nothing was changed."])
            return

        wrong_language = _language_check(app)
        if wrong_language:
            _ui.messageBox(wrong_language, "FusionZhTW")
            _log(["Skipped: user language is not English; nothing was changed."])
            return

        missing = [p for p in (DICT_PATH, DICT_LONG_PATH) if not os.path.exists(p)]
        if missing:
            _ui.messageBox(
                "Translation table not found.\n\n"
                "Run build_dict.py outside Fusion first.\n\n"
                + "\n".join(missing),
                "FusionZhTW",
            )
            return

        t_start = time.perf_counter()
        with open(DICT_PATH, encoding="utf-8") as f:
            table = json.load(f)
        with open(DICT_LONG_PATH, encoding="utf-8") as f:
            tips = json.load(f)
        t_load = time.perf_counter()
        log.append(f"Tables: {len(table)} names / {len(tips)} descriptions")

        n_cmd, n_tip, n_tab, n_panel = _apply(_ui, table, tips, log)
        log.append(f"  load tables      : {(t_load - t_start) * 1000:8.0f} ms")
        log.append(f"  RUN TOTAL        : "
                   f"{(time.perf_counter() - t_start) * 1000:8.0f} ms")
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
