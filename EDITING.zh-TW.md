# 編輯翻譯對照表

*[English](EDITING.md) · 繁體中文（台灣）*

產生的對照表是 Autodesk 簡體中文資料的機器轉換結果。它是起點，而非完成品：
OpenCC 轉換字形與一般詞彙，卻完全不懂 CAD 術語，因此 `Extrude` 會變成 `拉伸`，
而不管台灣業界實際慣用什麼說法。

本文說明如何安全地修正它們。

---

## 工作流程

```bash
python csv_tools.py export     # zh_tw.json / zh_tw_long.json -> .csv
                               # 編輯 CSV
python csv_tools.py import     # .csv -> 寫回 .json
python csv_tools.py check      # 回報譯文遺漏的符號
```

接著重新啟動 Fusion。增益集僅在啟動時讀取對照表。

會產生兩個檔案，對應兩份對照表：

| 檔案 | 列數 | 供應對象 |
|---|---|---|
| `zh_tw.csv` | 13,998 | 功能區指令名稱、頁籤名稱、面板名稱 |
| `zh_tw_long.csv` | 22,975 | 工具提示與說明文字 |

兩者都是相同的兩欄：

| 欄位 | 可以編輯嗎？ |
|---|---|
| `english` | **不可。** 這是用來與 Fusion 自身標籤比對的鍵，改了該條目就不再比對成功 |
| `traditional` | 可以。這是實際顯示在介面上的內容 |

請從您實際會用到的指令著手。修正每天都會碰到的三十個術語，
價值遠高於審閱一萬四千個您從未見過的條目。

---

## 必須保留的符號

`english` 欄並不是單純的文字，它帶有介面實際會用到的控制字元；
拿掉其中任何一個，改變的是行為而不只是措辭。

| 文字中的符號 | 意義 | 拿掉的後果 |
|---|---|---|
| 字母前的 `&` | Alt 快速鍵。該字母會加底線，`&` 本身不顯示 | 鍵盤快速鍵失效 |
| 結尾的 `...` | 表示會開啟對話方塊，而非立即執行 | 使用者無法分辨兩者 |
| `%1%`、`{0}` | 執行階段會填入的值 | 文字損壞，或顯示原始佔位符 |
| `<b>` `<br>` `<p>` `<a>` | Fusion 會轉譯的標記 | 版面損壞。`<br>` 還是增益集片段比對的依據 |
| `href="..."` | 說明連結的目標 | 連結失效 |
| `(...)` | 快速鍵容器、狀態（`(All)`）或複數（`Row(s)`） | 視情況而定，移除前請先判讀 |

### 快速鍵

中文無法在詞中標示快速鍵，因此慣例是附加在括號內。產生的對照表已遵循此作法：

```
"&Add Row"  ->  "新增行(&A)"
"&Close"    ->  "關閉(&C)"
```

同一個選單內的字母必須唯一，否則會互相衝突，其中一個將失效。

### 標記

標記請原樣保留，包含屬性在內：

```
"...unavailable.<br/><br/><a href="https://help.autodesk.com/...">Learn more</a>"
```

翻譯標記之間的文字，而不是標記本身，且絕對不要修改 `href` 的值。

---

## Excel 會破壞部分資料列，除非您加以防範

CSV 以帶 BOM 的 UTF-8 寫出，因此 Excel 能正確顯示中文，這部分已經處理好。
但另外兩點沒有，而且都會造成無聲的損壞。

**有 79 個條目以 `+`、`-`、`=` 或 `@` 開頭**——例如 `+X Offset`、
`- Additional load cases will be removed`。Excel 會將它們判讀為公式。
以雙擊方式開啟並存檔後，它們會變成 `#NAME?` 或錯誤值，原文就此消失。

**另有兩個條目分別是單獨的 `,` 與 `.`**，Excel 可能將其重新格式化為數字。

要避免這兩種情況，請不要雙擊開啟檔案，改用匯入：

1. 開啟 Excel 並建立空白活頁簿
2. `資料` → `從文字/CSV`
3. 選擇檔案，將**檔案原始格式**設為 `65001: Unicode (UTF-8)`
4. 點選 `載入` 旁的箭頭 → `轉換資料`
5. 在 Power Query 中選取兩個欄位，將型別設為**文字**
6. `關閉並載入`，編輯完成後選擇 `另存新檔` → `CSV UTF-8 (逗號分隔)`

若覺得這樣太過繁瑣，可改用純文字編輯器（VS Code、Notepad++），
或 LibreOffice Calc——它在開啟時會詢問欄位型別，兩欄都指定為「文字」即可。
Google 試算表也可以：`檔案` → `匯入` → 取消勾選*將文字轉換為數字、日期和公式*。

無論採用哪種方式，事後都請執行 `python csv_tools.py check`。

---

## 檢查成果

```bash
python csv_tools.py check
```

它會比對每一列的兩側，回報不一致之處：

```
zh_tw.json  [names]  13998 entries
  accelerator: 25 -- & marks the Alt shortcut; dropping it removes the shortcut
      '&Cancel'
   -> '取消'
  ellipsis: 4 -- ... tells the user a dialog will open
      'Add...'
   -> '新增'
```

檢查項目包含佔位符、HTML 標記、連結目標、快速鍵、結尾 `...` 與多餘空白。

**數字不為零是正常的。** Autodesk 自己的簡體中文資料本身就有 90 處這類不一致，
沒有一處是本專案造成的。請在開始編輯前先執行一次、完成後再執行一次，比較兩個數字。
數字上升就表示您遺漏了某些符號。

前後空白不會經由這個流程出現，因為 `import` 會自動去除。
該檢查項目是為了直接以 JSON 手動編輯的情況而保留。

---

## 不會遺失任何東西

每次寫入前都會先建立帶時間戳記的副本：

```
backups/zh_tw.20260818-125617966.json
backups/zh_tw_long.20260818-125618558.json
```

`csv_tools.py import` 與 `build_dict.py` 都會這麼做，每份對照表保留最新 20 個世代。
要復原時，將該檔案複製回 `zh_tw.json` 即可。由於檔名依時間排序，
最新的世代就是字母順序中的最後一個。

這一點對 `build_dict.py` 尤其重要：重建會從 StringTable 重新產生兩份對照表，
並**捨棄您所做的每一項修正**。備份是唯一的退路，
因此若打算重建，也請一併保留您編輯過的 CSV。

若匯入會刪除超過 10% 的條目，將直接被拒絕：

```
zh_tw.json: REFUSED -- 13997 of 13998 entries (99%) would be removed.
    zh_tw.csv has 1 rows; the table has 13998.
    Re-export, or pass --force if the deletion is intended.
```

這通常表示檔案被截斷，或試算表在套用篩選的狀態下存檔。請重新匯出再來一次。
若確實有意刪除，可用 `--force` 略過此保護。

---

## 匯入如何處理不完整的資料列

| 情況 | 結果 |
|---|---|
| `english` 為空 | 略過該列，並回報行號 |
| `traditional` 為空 | 略過該列並回報 |
| 同一個 `english` 出現兩次 | 以最後一筆為準，並回報 |
| 前後有空白 | 自動去除，不另行提示 |
| 欄位名稱錯誤 | 完全不寫入任何內容 |

除了空白之外，沒有任何內容會被無聲地捨棄。

---

## 實例

```
english,traditional
"Extrude","拉伸"          <- 機器轉換結果
"Extrude","擠出"          <- 您的修正
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

重新啟動 Fusion，功能區就會顯示 `擠出`。
