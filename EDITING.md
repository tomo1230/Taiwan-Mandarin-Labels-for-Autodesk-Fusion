# Editing the translation tables

*English · [繁體中文（台灣）](EDITING.zh-TW.md)*

The generated tables are a machine conversion of Autodesk's Simplified Chinese
data. They are a starting point, not a finished translation: OpenCC converts
characters and general vocabulary but knows nothing about CAD terminology, so
`Extrude` arrives as `拉伸` regardless of what Taiwanese practice would use.

This describes how to correct them safely.

---

## The workflow

```bash
python csv_tools.py export     # zh_tw.json / zh_tw_long.json -> .csv
                               # edit the CSV
python csv_tools.py import     # .csv -> back into the .json
python csv_tools.py check      # report symbols the translation dropped
```

Then restart Fusion. The add-in reads the tables at startup only.

Two files are produced, matching the two tables:

| File | Rows | Feeds |
|---|---|---|
| `zh_tw.csv` | 13,998 | ribbon command names, tab names, panel names |
| `zh_tw_long.csv` | 22,975 | tooltips and description text |

Both have the same two columns:

| Column | Edit it? |
|---|---|
| `english` | **No.** This is the lookup key matched against Fusion's own labels. Change it and the entry simply stops matching |
| `traditional` | Yes. This is what appears in the UI |

Start with the commands you actually use. Correcting thirty terms you touch
daily is worth more than reviewing fourteen thousand you never see.

---

## Symbols you must carry across

The `english` side is not plain prose. It carries control characters the UI
acts on, and dropping one changes behaviour rather than wording.

| In the text | Meaning | If you drop it |
|---|---|---|
| `&` before a letter | Alt shortcut. The letter is underlined; the `&` itself is not drawn | The keyboard shortcut stops working |
| `...` at the end | A dialog will open, rather than the command running immediately | The user cannot tell the two apart |
| `%1%`, `{0}` | A value substituted at runtime | The text breaks, or shows a raw placeholder |
| `<b>` `<br>` `<p>` `<a>` | Markup Fusion renders | Layout breaks. `<br>` also drives the add-in's fragment matching |
| `href="..."` | Help link target | The link goes nowhere |
| `(...)` | An accelerator holder, a state (`(All)`), or a plural (`Row(s)`) | Depends — read it before removing |

### Accelerators

Chinese cannot mark an accelerator mid-word, so the convention is to append it
in parentheses. The generated tables already follow it:

```
"&Add Row"  ->  "新增行(&A)"
"&Close"    ->  "關閉(&C)"
```

Keep the letters unique within a single menu, or they collide and one of them
stops working.

### Markup

Leave tags exactly as they are, including attributes:

```
"...unavailable.<br/><br/><a href="https://help.autodesk.com/...">Learn more</a>"
```

Translate the words between the tags, not the tags themselves, and never edit
a `href` value.

---

## Excel will corrupt some rows unless you stop it

The CSV is written UTF-8 with a BOM so Excel opens Chinese correctly. That part
is handled. Two things are not, and both cause silent damage.

**79 entries begin with `+`, `-`, `=` or `@`** — `+X Offset`, `- Additional
load cases will be removed`, and so on. Excel reads those as formulas. Opening
the file by double-clicking and saving turns them into `#NAME?` or an error
value, and the original text is gone.

**Two entries are `,` and `.` alone**, which Excel may reformat as numbers.

To avoid both, do not double-click the file. Import it instead:

1. Open Excel with a blank workbook
2. `Data` → `From Text/CSV`
3. Pick the file, set **File Origin** to `65001: Unicode (UTF-8)`
4. Click the arrow beside `Load` → `Transform Data`
5. In Power Query, select both columns and set the type to **Text**
6. `Close & Load`, edit, then `Save As` → `CSV UTF-8 (Comma delimited)`

If that is more ceremony than you want, use a plain text editor (VS Code,
Notepad++) or LibreOffice Calc, which asks for the column type on open and can
be told `Text` for both columns. Google Sheets works too: `File` → `Import` →
uncheck *Convert text to numbers, dates, and formulas*.

Either way, run `python csv_tools.py check` afterwards.

---

## Checking your work

```bash
python csv_tools.py check
```

It compares the two sides of every row and reports what disagrees:

```
zh_tw.json  [names]  13998 entries
  accelerator: 25 -- & marks the Alt shortcut; dropping it removes the shortcut
      '&Cancel'
   -> '取消'
  ellipsis: 4 -- ... tells the user a dialog will open
      'Add...'
   -> '新增'
```

It checks placeholders, HTML tags, link targets, accelerators, trailing `...`
and stray whitespace.

**A count above zero is normal.** Autodesk's own Simplified Chinese data
already contains 90 such mismatches, none of them introduced by this project.
Run `check` before you start and again when you finish, and compare the two
numbers. A rise means you dropped something.

Leading and trailing spaces never appear via this route, because `import`
strips them. That check exists for tables edited by hand as JSON.

---

## Nothing is lost

Every write is preceded by a timestamped copy:

```
backups/zh_tw.20260818-125617966.json
backups/zh_tw_long.20260818-125618558.json
```

Both `csv_tools.py import` and `build_dict.py` do this, and the twenty newest
generations of each table are kept. To recover, copy the file back over
`zh_tw.json`. The newest generation is the last one alphabetically, since the
name sorts chronologically.

This matters most with `build_dict.py`: rebuilding regenerates both tables from
StringTable and **discards every correction you have made**. The backup is the
only way back, so keep your edited CSV as well if you plan to rebuild.

An import that would delete more than 10% of the entries is refused outright:

```
zh_tw.json: REFUSED -- 13997 of 13998 entries (99%) would be removed.
    zh_tw.csv has 1 rows; the table has 13998.
    Re-export, or pass --force if the deletion is intended.
```

That usually means a truncated file, or a spreadsheet saved with a filter
applied. Re-export and start again. `--force` overrides it when the deletion is
deliberate.

---

## What import does with imperfect rows

| Situation | Result |
|---|---|
| `english` empty | Row skipped, reported with its line number |
| `traditional` empty | Row skipped, reported |
| Same `english` twice | Last value wins, reported |
| Leading/trailing spaces | Stripped silently |
| Column names wrong | Nothing is written at all |

Nothing is dropped in silence except whitespace.

---

## A worked example

```
english,traditional
"Extrude","拉伸"          <- machine output
"Extrude","擠出"          <- your correction
```

```bash
python csv_tools.py import
```

```
zh_tw.json          13998 entries  [names]
    changed 1, added 0, removed 0
      'Extrude': '拉伸' -> '擠出'
    backup: backups/zh_tw.20260818-131022441.json
```

Restart Fusion, and the ribbon reads `擠出`.
