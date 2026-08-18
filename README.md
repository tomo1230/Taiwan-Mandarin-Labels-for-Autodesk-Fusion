# FusionZhTW — Taiwan Mandarin Labels for Autodesk Fusion / Autodesk Fusion 台灣華語標籤增益集

*English · [繁體中文（台灣）](README.zh-TW.md)*

An Autodesk Fusion add-in that relabels the ribbon in **Taiwan Mandarin (zh-TW)** —
Traditional Chinese script with Taiwan vocabulary.

Fusion does not ship a `zh-TW` user language. This add-in does not add one. It
rewrites the labels the Fusion API exposes at runtime, which covers the ribbon
and little else. Read [Scope](#scope) before deciding whether this is useful to you.

> **Not Taiwanese Hokkien.** The target is Taiwan Mandarin (國語), the language
> Fusion would list as "Chinese (Traditional)". It is also not Hong Kong
> Traditional, which uses different vocabulary (軟體 vs 軟件).

---

## At a glance

**What it does**

- Relabels ribbon command names, tooltips, tab names and panel names
  — 2,472 / 1,161 / 83 / 345 strings on Fusion 2704.1.53
- Reverses cleanly: stop the add-in, or simply restart Fusion
- Touches nothing on disk — no file in your Fusion installation is modified
- **Applies at Fusion startup only** — see [Why startup only](#why-startup-only)

**What it does not do**

- **Does not add `zh-TW` as a Fusion user language.** The language menu is unchanged
- **Dialog contents stay English.** Command dialogs, the browser tree, the workspace
  switcher, drop-down menus, the data panel and the home tab are all blocked by the
  Fusion API — see [What blocks the rest](#what-blocks-the-rest). Expect a
  **mixed-language UI**, permanently
- **Requires the UI language set to English.** It cannot run on top of a Japanese,
  German or any other localised UI — the lookup keys are English source strings
- **Does not correct CAD terminology.** Translations are machine-converted from the
  Simplified Chinese build, so terms like `Extrude` → `拉伸` may not match Taiwanese
  CAD convention. Expect to hand-edit the commands you use most
- **Is not a translation of Fusion.** It covers roughly 70% of the tooltips that
  exist, and nothing outside the ribbon

If a fully Traditional Chinese Fusion is what you need, this is not it, and no
add-in can be. Only Autodesk can ship that.

---

## Why zh-TW cannot simply be enabled

Fusion's language list is defined in `StringTable/<locale>/NsBaseCore10.xml` and
contains 15 languages, including `Chinese (Traditional)`. Only 11 of them are
actually installed. `zh-TW` is one of the four that are named but absent.

Inspecting the deployment database (`%LOCALAPPDATA%\Autodesk\webdeploy\meta\registry`,
a SQLite file listing all 84 packages and 101,450 files) shows **no per-language
packages exist**. Package identities are functional — `Qt`, `Python`, `NODEJS`,
`ASM`, `ATF`, `drawing`, `FUSIONDOCSTREAMER` — and the `StringTable` files for
every locale are baked into ten of those functional packages.

Locales recorded in the registry:

```
de-de 177 / ja-jp 177 / zh-cn 177 / fr-fr 175 / it-it 175
es-es 169 / ko-kr 169 / pl-pl 165 / pt-br 165 / tr-tr 165
en-us 156 / hr-hr 2                              total 1,872 files
```

There is no `zh-tw` entry and no mechanism to fetch one. Translations are compiled
into the build, not downloaded on demand. Enabling zh-TW requires Autodesk to ship it.

---

## How it works

1. **`build_dict.py`** (run outside Fusion) reads `StringTable/zh-CN/*.xml`.
   Every line carries both the English source and the Simplified Chinese
   translation:

   ```xml
   <label commandName="A360RenderCmd_E1" devLabel="Render Settings Error" translation="渲染设置错误"/>
   ```

   Those pairs go through OpenCC's `s2twp` profile, which converts Simplified to
   Traditional **and** substitutes Taiwan vocabulary (软件 → 軟體, not 軟件),
   producing an English → Taiwan Mandarin table.

2. **`FusionZhTW.py`** enumerates `ui.commandDefinitions` at startup and looks up
   each `name` and `tooltip` by its English text, writing back the translation.
   Tabs and panels are handled the same way.

Lookup is keyed on **English source text, not command IDs.** The `commandName`
attributes in StringTable belong to a different namespace than
`CommandDefinition.id` — `SketchCreate` and `ExtrudeCmd` do not appear in
StringTable at all — so ID matching does not work.

### Two tables, deliberately

| File | Used for | Limit | Entries |
|---|---|---|---|
| `zh_tw.json` | display names (`name`) | ≤ 40 chars, no markup, no newlines | 13,998 |
| `zh_tw_long.json` | tooltips and descriptions | ≤ 300 chars, markup allowed | 22,975 |

Strings containing `%1%` are excluded from both — those placeholders are filled
at runtime and translating them corrupts the output.

### Tooltips need fuzzy matching

Runtime tooltips are not verbatim StringTable entries. Fusion concatenates
several entries with `<br><br>`, and trailing punctuation drifts:

| Runtime | StringTable |
|---|---|
| `...displays here` | `...displays here.` |
| `Generates realistic renderings of the design.<br><br>` | `Generates realistic renderings of the design.` |
| `Specifies which object types can be selected.<br><br>Use Select All to...` | two separate entries |

`_translate_rich()` splits on `<br>`, translates each fragment independently,
and rejoins with the separators intact. A normalised index absorbs trailing
`.`, `:`, `。`, `：`. If no fragment resolves, the string is left untouched
rather than partially translated.

Exact matching alone resolved 35 tooltips. Fragment matching resolves **1,161**.

---

## Scope

Measured on Fusion 2704.1.53, English UI:

| Area | Result |
|---|---|
| Command names | **2,472** replaced |
| Tooltips | **1,161** replaced |
| Panel names | **345** replaced |
| Tab names | **83** replaced |
| Drop-down menus | Not possible |
| Workspace switcher | Not possible |
| Dialog contents | Not possible |
| Browser tree | Not possible |
| Data panel, home tab | Not possible |

The result is a **mixed-language UI**: the ribbon reads in Chinese, dialogs and
the browser tree stay in English. Decide whether that trade is acceptable before
installing.

Of 3,099 command definitions, 1,443 have no tooltip at all, leaving 1,656 with
content — so tooltip coverage is roughly 70% of what exists.

### What blocks the rest

The TypeScript definitions in `API/TypeScript/@adsk/fusion/core.d.ts` do not
match the shipped implementation. Verified by probing the running product:

| Declared in `core.d.ts` | Actual behaviour |
|---|---|
| `DropDownControl.text: string` | Attribute does not exist (`AttributeError`) |
| `DropDownControl.name: string` | Reading raises `RuntimeError: InternalValidationError : nuInputControl` |
| `Workspace.tooltip` / `tooltipDescription` writable | All 52 writes rejected: *"The tooltip text displayed for the native workspaces could not be modified"* |
| `CommandDefinition.name: string` | Writable, including on native commands |
| `Workspace.name` | Read-only, as declared |
| `CommandInput.name` | Read-only, as declared |

There are 570 `DropDownControl` instances under the panels (alongside 15,638
`CommandControl` and 3,174 `SeparatorControl`), so the targets exist — they are
simply unreachable.

Both were implemented, measured at zero effect, and then removed rather than
left in as disabled branches.

**Do not trust `core.d.ts` alone.** Probe writes against the running product.

### Why startup only

Renaming command definitions *after* Fusion has finished starting corrupts the
workspace switcher: all entries collapse to one identical label, so you cannot
tell the workspaces apart. Applied during startup, the same renames are harmless.

Bisection over the 2,472 renames located a trigger at index 10 —
`VisibilityToggleCmd`, whose name is `Show/Hide`. Excluding it was not enough;
renaming the remaining 2,470 still broke the switcher, so several unrelated
definitions can each set it off on their own. The visible symptom is misleading
too: the duplicated label is the name of a *different* command
(`ActivateEnvironmentCommand`, whose name is literally `Workspace`), which Fusion
falls back to when it can no longer resolve the real ones.

Chasing every trigger would mean many rounds of manual bisection for no benefit,
because **the switcher cannot be translated anyway** — `Workspace.name` is
read-only. There was never anything to gain there; the only requirement is to
leave it intact. Restricting the add-in to startup does that with certainty.

`run(context)` checks `IsApplicationStartup` and returns early otherwise,
changing nothing.

---

## Installation

### 1. Place the folder

Copy the whole folder into Fusion's add-ins directory:

- **Windows:** `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\FusionZhTW`
- **macOS:** `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/FusionZhTW`

> **The folder name must match the file names exactly.** Fusion locates an add-in
> by looking for `<FolderName>.manifest` and `<FolderName>.py` inside a folder of
> the same name. Renaming the folder to `FusionZhTW-main` — which is what GitHub's
> ZIP download produces — makes the add-in invisible in the dialog with no error
> message. Rename it back to `FusionZhTW`.

The layout Fusion expects:

```
AddIns/
└── FusionZhTW/
    ├── FusionZhTW.manifest   <- name must match the folder
    ├── FusionZhTW.py         <- name must match the folder
    ├── build_dict.py
    ├── zh_tw.json            <- created in step 2
    └── zh_tw_long.json       <- created in step 2
```

### 2. Generate the translation tables

The generator runs on a normal Python installation, not Fusion's embedded
interpreter:

```bash
python -m pip install opencc-python-reimplemented
```

```bash
python build_dict.py
```

It locates the newest `webdeploy` version folder automatically and writes both
JSON files next to itself. Expect output along these lines:

```
Wrote: zh_tw.json [names] 13998 entries (159 ambiguous, most frequent reading kept)
Wrote: zh_tw_long.json [descriptions] 22975 entries (214 ambiguous, most frequent reading kept)
```

If it exits with `StringTable/zh-CN not found`, your installation has no Simplified
Chinese data to convert from, and this add-in cannot work.

### 3. Set Fusion's user language to English

Click the user icon → `Preferences` → `General` → `User language` → **English**,
then restart Fusion.

This is required, not cosmetic. The tables are keyed on English source text; with
a Japanese or German UI, `cd.name` returns that language and nothing matches. The
setting is stored in your Autodesk account, so the restart needs a network connection.

The add-in checks `userLanguage` before touching anything. On a non-English UI it
names the language it found, explains why there is nothing to match, and changes
nothing — rather than silently reporting zero replacements.

### 4. Run the add-in

`Utilities` → `Add-Ins` → **Add-Ins** tab → select `FusionZhTW` → tick
**Run on Startup**, then **restart Fusion**.

> **Startup only, by design.** Pressing `Run` mid-session does nothing except
> show a reminder. Renaming command definitions while Fusion is already running
> corrupts the workspace switcher — every entry collapses to the same label and
> the menu becomes unusable. See [Why startup only](#why-startup-only).

A summary dialog reports what was replaced. Set `SHOW_SUMMARY = False` in
`FusionZhTW.py` to suppress it once you no longer need it; the same counts are
always written to `last_run.log`.

### Verifying

A healthy run reports counts in these ranges (Fusion 2704.1.53):

```
Command names : 2472
Tooltips      : 1161
Tab names     : 83
Panel names   : 345
```

### Troubleshooting

| Symptom | Cause |
|---|---|
| Add-in absent from the dialog | Folder name does not match the `.py` / `.manifest` names |
| Only a reminder appears, nothing changes | `Run` was pressed mid-session — tick *Run on Startup* and restart |
| `FusionZhTW needs the user language set to English` | Exactly that — switch it in Preferences and restart |
| `Translation table not found` | Step 2 was skipped, or the JSON files sit elsewhere |
| Counts far below the reference | Run the diagnostic script (see [Files](#files)) |
| Ribbon partly English | Expected — StringTable has no entry for those commands |

### Reverting

`stop()` restores every string it replaced, in reverse order.

Beyond that, labels are **runtime state that is never persisted**. Restarting
Fusion without the add-in returns the original UI unconditionally — even after a
crash, and even if `stop()` fails. If a restore is skipped because its object was
already destroyed (which can happen when workspaces are rebuilt), restarting clears it.

---

## Files

| File | Purpose |
|---|---|
| `FusionZhTW.py` | The add-in |
| `FusionZhTW.manifest` | Add-in descriptor |
| `build_dict.py` | Table generator, run outside Fusion |
| `csv_tools.py` | Exports the tables to CSV and reads them back, run outside Fusion |
| `tablebackup.py` | Timestamped backups, used by the two tools above |
| `zh_tw.json` | Generated — display names |
| `zh_tw_long.json` | Generated — tooltips and descriptions |
| `last_run.log` | Written on each run with per-category counts |

A companion diagnostic script lives in `API/Scripts/FusionZhTW_diag/`. It probes
attribute readability and attempts writes (using a zero-width space, always
restored in a `finally` block), then reports control type distributions and
tooltip hit rates to `diag.txt`. Use it when counts come back unexpectedly low.

Note that its section 4 matches exactly and will report far fewer tooltip hits
than the add-in achieves, which applies fragment matching.

---

## Translation quality

OpenCC converts characters and general vocabulary. **It does not know CAD
terminology.** `Extrude` comes through as `拉伸`, carried over from the Simplified
Chinese build, which may not match Taiwanese CAD convention.

Correcting the few dozen commands you use daily is worth more than the bulk import.

### Editing in a spreadsheet

The tables are plain JSON keyed on English text, so small fixes can be made in
the file directly:

```json
{ "Extrude": "your preferred term" }
```

For anything larger, round-trip them through CSV:

```bash
python csv_tools.py export
```

That writes `zh_tw.csv` and `zh_tw_long.csv` as UTF-8 with a BOM, which is what
Excel needs to show Chinese correctly. Edit the `traditional` column — leave
`english` alone, since it is the key matched against Fusion's own labels, and
changing it just disables that entry. Then:

```bash
python csv_tools.py import
```

The previous JSON is kept as `.json.bak`, and the run reports what changed:

```
zh_tw.json          13998 entries  [names]
    changed 2, added 1, removed 0
      'Extrude': '拉伸' -> '擠出'
```

Rows with an empty column are skipped and reported; duplicate keys take the last
value. An import that would drop more than 10% of the entries is refused, since
that usually means a truncated or filtered CSV — pass `--force` if the deletion
is deliberate.

### Symbols you must carry across

The `english` column is not plain prose. It carries control characters the UI
acts on, and dropping one changes behaviour rather than wording.

| In the text | Meaning | If you drop it |
|---|---|---|
| `&` before a letter | Alt shortcut; the letter is underlined, the `&` is not drawn | The keyboard shortcut stops working |
| `...` at the end | A dialog will open, rather than the command running immediately | The user cannot tell the two apart |
| `%1%`, `{0}` | A value substituted at runtime | The text breaks, or shows a raw placeholder |
| `<b>` `<br>` `<p>` `<a>` | Markup Fusion renders | Layout breaks; `<br>` also drives the add-in's fragment matching |
| `href="..."` | Help link target | The link goes nowhere |
| `(...)` | Either an accelerator holder, a state (`(All)`), or a plural (`Row(s)`) | Depends — read it before removing |

Chinese cannot mark an accelerator mid-word, so the convention is to append it
in parentheses. The generated tables already follow it:

```
"&Add Row"  ->  "新增行(&A)"
"&Close"    ->  "關閉(&C)"
```

Keep accelerators unique within one menu, or they collide.

To find entries where the two sides disagree:

```bash
python csv_tools.py check
```

It reports placeholders, tags, link targets, accelerators, trailing `...` and
stray whitespace, with examples:

```
zh_tw.json  [names]  13998 entries
  accelerator: 25 -- & marks the Alt shortcut; dropping it removes the shortcut
      '&Cancel'
   -> '取消'
```

Autodesk's own Simplified Chinese data already contains 90 such mismatches, so
a non-zero count is expected. Run it before and after editing and compare,
rather than trying to reach zero.

### Backups

Both `build_dict.py` and `csv_tools.py` copy the current tables into `backups/`
before overwriting them, named with the time taken:

```
backups/zh_tw.20260818-125617966.json
```

This matters because rebuilding with `build_dict.py` regenerates both tables
from StringTable and discards every hand-correction. The twenty most recent
generations of each table are kept and older ones are pruned.

Recovering an edit means copying the file back over `zh_tw.json` — the newest
generation is the last one alphabetically, since the name sorts chronologically.

Where one English string had several Simplified translations, the most frequent
was taken: 159 such cases in the name table, 214 in the description table.

---

## Licensing — read before publishing a fork

`zh_tw.json` and `zh_tw_long.json` are **derived from Autodesk's proprietary
translation data**, extracted from a local Fusion installation. Redistributing
them is very likely a licence violation.

**Commit the generator, not the generated tables.** Each user runs `build_dict.py`
against their own installation.

```gitignore
zh_tw.json
zh_tw_long.json
last_run.log
__pycache__/
```

The code in this repository is the author's own work; the extracted strings are not.

---

## Verified against

- Autodesk Fusion **2704.1.53** (webdeploy `61bf25b220a2d0307c84c301e65a59ac225d9a1e`)
- Windows 11 Pro
- Python 3.12.10 with `opencc-python-reimplemented` for the build step

Attribute availability is version-specific. If counts drop to zero after a Fusion
update, run the diagnostic script before assuming the add-in is at fault.
