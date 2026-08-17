"""Diagnostic script for the parts FusionZhTW cannot reach.

Separates the causes behind zero drop-downs, zero workspaces and the low
tooltip count. Writes diag.txt next to itself.

Run with the add-in stopped, so the UI is still in English.
"""

import json
import os
import traceback
from collections import Counter

import adsk.core

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "diag.txt")

ADDIN = os.path.join(
    os.environ.get("APPDATA", ""),
    "Autodesk", "Autodesk Fusion 360", "API", "AddIns", "FusionZhTW",
)


def run(context):
    ui = None
    L = []
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface

        # Loading the tables separates "string was read but is absent from the
        # table" from the other failure modes.
        table = tips = {}
        try:
            with open(os.path.join(ADDIN, "zh_tw.json"), encoding="utf-8") as f:
                table = json.load(f)
            with open(os.path.join(ADDIN, "zh_tw_long.json"), encoding="utf-8") as f:
                tips = json.load(f)
        except Exception as e:
            L.append(f"[failed to load tables] {e}")
        L.append(f"Tables: {len(table)} names / {len(tips)} descriptions")

        # ---------- 1. Workspaces: are writes actually accepted? ----------
        L.append("\n===== 1. Workspaces (write probe) =====")
        L.append("  core.d.ts marks tooltip/tooltipDescription writable. Test it.")
        n_ok = n_ng = 0
        for ws in ui.workspaces:
            try:
                wid = ws.id
            except Exception as e:
                L.append(f"  <unreachable> {e}")
                continue
            for attr in ("tooltip", "tooltipDescription"):
                try:
                    before = getattr(ws, attr)
                except Exception as e:
                    L.append(f"  {wid}.{attr}: read failed {e}")
                    continue
                if not before:
                    continue
                probe = before + "​"      # append an invisible character
                verdict = ""
                try:
                    setattr(ws, attr, probe)
                    after = getattr(ws, attr)
                    if after == probe:
                        verdict = "write OK"
                        n_ok += 1
                    else:
                        verdict = f"ignored (still {after[:30]!r})"
                        n_ng += 1
                except Exception as e:
                    verdict = f"exception {e}"
                    n_ng += 1
                finally:
                    try:
                        setattr(ws, attr, before)   # always restore
                    except Exception:
                        pass
                if n_ok + n_ng <= 12:
                    L.append(f"  {wid}.{attr}: {verdict}")
        L.append(f"  -> {n_ok} writes succeeded / {n_ng} failed")

        # ---------- 2. Control types under the panels ----------
        L.append("\n===== 2. Control type distribution (under panels) =====")
        types = Counter()
        drop_samples = []
        panels_seen = 0
        panels_err = 0
        controls_total = 0

        for ws in ui.workspaces:
            try:
                tabs = ws.toolbarTabs
            except Exception:
                continue
            for tab in tabs:
                try:
                    panels = tab.toolbarPanels
                except Exception:
                    continue
                for panel in panels:
                    panels_seen += 1
                    try:
                        ctrls = panel.controls
                        n = ctrls.count
                    except Exception as e:
                        panels_err += 1
                        if panels_err <= 3:
                            L.append(f"  [controls unavailable] {panel.id}: {e}")
                        continue
                    controls_total += n
                    for i in range(n):
                        try:
                            c = ctrls.item(i)
                        except Exception:
                            types["<item raised>"] += 1
                            continue
                        if c is None:
                            types["<None>"] += 1
                            continue
                        try:
                            types[c.objectType] += 1
                        except Exception:
                            types["<objectType raised>"] += 1
                        dd = adsk.core.DropDownControl.cast(c)
                        if dd is not None and len(drop_samples) < 10:
                            # Probe each attribute separately so one failure
                            # does not hide the rest.
                            info = {"panel": panel.id}
                            for attr in ("id", "name", "text", "objectType"):
                                try:
                                    info[attr] = repr(getattr(dd, attr))
                                except Exception as e:
                                    info[attr] = f"<{type(e).__name__}: {e}>"
                            # Write probe
                            for attr in ("name", "text"):
                                try:
                                    before = getattr(dd, attr)
                                except Exception as e:
                                    info[attr + "_write"] = f"unreadable({type(e).__name__})"
                                    continue
                                try:
                                    setattr(dd, attr, (before or "") + "​")
                                    ok = getattr(dd, attr) != before
                                    info[attr + "_write"] = "OK" if ok else "ignored"
                                    setattr(dd, attr, before)
                                except Exception as e:
                                    info[attr + "_write"] = f"exception({type(e).__name__})"
                            info["in_table"] = (
                                info.get("name", "").strip("'") in table
                            )
                            drop_samples.append(info)

        L.append(f"  {panels_seen} panels ({panels_err} with unavailable controls) "
                 f"/ {controls_total} controls")
        for t, n in types.most_common():
            L.append(f"    {n:6}  {t}")

        L.append("\n  DropDownControl samples:")
        if not drop_samples:
            L.append("    (none -- no drop-downs directly under any panel)")
        for s in drop_samples:
            L.append("    " + "  ".join(f"{k}={v}" for k, v in s.items()))

        # ---------- 3. ui.toolbars ----------
        L.append("\n===== 3. ui.toolbars =====")
        try:
            tbs = ui.toolbars
            L.append(f"  toolbars.count = {tbs.count}")
            for i in range(tbs.count):
                tb = tbs.item(i)
                if tb is None:
                    L.append(f"    [{i}] None")
                    continue
                try:
                    cc = tb.controls.count
                except Exception as e:
                    L.append(f"    [{i}] id={tb.id} controls unavailable {e}")
                    continue
                kinds = Counter()
                for j in range(cc):
                    c = tb.controls.item(j)
                    if c is None:
                        continue
                    try:
                        kinds[c.objectType.split(":")[-1]] += 1
                    except Exception:
                        pass
                L.append(f"    [{i}] id={tb.id} controls={cc} {dict(kinds)}")
        except Exception as e:
            L.append(f"  <exception> {e}")

        # ---------- 4. What CommandDefinition.tooltip really holds ----------
        # Note: this section matches exactly, unlike the add-in, which also
        # splits on <br> and normalises trailing punctuation. Expect the hit
        # count here to read lower than what the add-in achieves.
        L.append("\n===== 4. CommandDefinition.tooltip in practice =====")
        defs = ui.commandDefinitions
        total = defs.count
        empty = miss = hit = err = 0
        miss_samples = []
        for i in range(total):
            try:
                cd = defs.item(i)
                if cd is None:
                    continue
                t = cd.tooltip
            except Exception:
                err += 1
                continue
            if not t or not t.strip():
                empty += 1
            elif t.strip() in tips:
                hit += 1
            else:
                miss += 1
                if len(miss_samples) < 15:
                    miss_samples.append((cd.id, t[:70]))
        L.append(f"  {total} definitions: {empty} empty / {hit} exact hits / "
                 f"{miss} missed / {err} raised")
        L.append("  Missed samples:")
        for cid, t in miss_samples:
            L.append(f"    {cid}: {t!r}")

        with open(OUT, "w", encoding="utf-8") as f:
            f.write("\n".join(L))
        ui.messageBox(f"Diagnostics written to:\n\n{OUT}", "FusionZhTW_diag")

    except Exception:
        msg = traceback.format_exc()
        try:
            with open(OUT, "w", encoding="utf-8") as f:
                f.write("\n".join(L) + "\n\n" + msg)
        except Exception:
            pass
        if ui:
            ui.messageBox("Diagnostics failed:\n\n" + msg, "FusionZhTW_diag")
