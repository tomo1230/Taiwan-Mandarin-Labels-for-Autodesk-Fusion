# FusionZhTW — Fusion 台灣華語標籤增益集 / Taiwan Mandarin Labels for Fusion

*[English](README.md) · 繁體中文（台灣）*

一個 Autodesk Fusion 增益集，將功能區的標籤改為**台灣華語（zh-TW）**——
繁體中文字，搭配台灣慣用詞彙。

Fusion 並未提供 `zh-TW` 使用者語言，本增益集也不會新增一個。它在執行階段改寫
Fusion API 所公開的標籤，涵蓋範圍僅止於功能區。安裝前請先閱讀[涵蓋範圍](#涵蓋範圍)。

> **並非台語（閩南語）。** 目標是台灣華語（國語），也就是 Fusion 會列為
> 「Chinese (Traditional)」的語言。也不是香港繁體，兩者詞彙有別（軟體 vs 軟件）。

---

## 一覽

**可以做到**

- 改寫功能區的指令名稱、工具提示、頁籤名稱與面板名稱
  —— 在 Fusion 2704.1.53 上為 2,472 / 1,161 / 83 / 345 個字串
- 可完全還原：停用增益集，或直接重新啟動 Fusion
- 不動硬碟上的任何檔案——不會修改 Fusion 安裝目錄中的任何內容
- **僅在 Fusion 啟動時套用**——請見[為何僅限啟動時](#為何僅限啟動時)

**無法做到**

- **不會新增 `zh-TW` 為 Fusion 的使用者語言。** 語言選單維持原狀
- **對話方塊內容維持英文。** 指令對話方塊、瀏覽器樹狀結構、工作區切換器、
  下拉式功能表、資料面板與首頁頁籤全數被 Fusion API 擋下——請見
  [其餘部分為何無法處理](#其餘部分為何無法處理)。介面將**長期處於中英混合狀態**
- **必須將介面語言設為 English。** 無法在日文、德文或其他在地化介面上運作，
  因為查找的鍵是英文原文
- **不會修正 CAD 專業術語。** 譯文由簡體中文版本機器轉換而來，
  因此 `Extrude` → `拉伸` 這類詞彙未必符合台灣 CAD 業界慣用說法。
  請預期需要手動修改您最常用的指令
- **這不是 Fusion 的中文化。** 涵蓋率約為現有工具提示的 70%，
  且功能區以外的區域完全不處理

若您需要的是完整繁體中文的 Fusion，這個專案並非解答，任何增益集也做不到。
只有 Autodesk 能提供。

---

## 為何無法直接啟用 zh-TW

Fusion 的語言清單定義於 `StringTable/<locale>/NsBaseCore10.xml`，共 15 種語言，
其中包含 `Chinese (Traditional)`。但實際安裝的只有 11 種，`zh-TW` 正是四個
「有名稱卻無內容」的語言之一。

檢視部署資料庫（`%LOCALAPPDATA%\Autodesk\webdeploy\meta\registry`，一個 SQLite
檔案，記錄全部 84 個套件與 101,450 個檔案）可知：**不存在任何語言別套件**。
套件的識別名稱皆以功能劃分——`Qt`、`Python`、`NODEJS`、`ASM`、`ATF`、`drawing`、
`FUSIONDOCSTREAMER`——所有語言的 `StringTable` 檔案都被編入其中十個功能套件內部。

註冊資料庫記錄的語言：

```
de-de 177 / ja-jp 177 / zh-cn 177 / fr-fr 175 / it-it 175
es-es 169 / ko-kr 169 / pl-pl 165 / pt-br 165 / tr-tr 165
en-us 156 / hr-hr 2                              合計 1,872 個檔案
```

其中沒有 `zh-tw`，也沒有任何取得它的機制。翻譯資料是編譯進產品版本的，
並非隨選下載。要啟用 zh-TW，只能等 Autodesk 自行提供。

---

## 運作方式

1. **`build_dict.py`**（在 Fusion 之外執行）讀取 `StringTable/zh-CN/*.xml`。
   每一行同時帶有英文原文與簡體中文譯文：

   ```xml
   <label commandName="A360RenderCmd_E1" devLabel="Render Settings Error" translation="渲染设置错误"/>
   ```

   這些配對經由 OpenCC 的 `s2twp` 設定處理，該設定會將簡體轉為繁體，
   **並且**替換為台灣慣用詞彙（软件 → 軟體，而非 軟件），
   產生英文 → 台灣華語的對照表。

2. **`FusionZhTW.py`** 在啟動時列舉 `ui.commandDefinitions`，以英文文字查找
   每個 `name` 與 `tooltip`，再將譯文寫回。頁籤與面板的處理方式相同。

查找的鍵是**英文原文，而非指令 ID**。StringTable 中的 `commandName` 屬性與
`CommandDefinition.id` 分屬不同體系——`SketchCreate` 與 `ExtrudeCmd` 在
StringTable 中根本不存在——因此以 ID 比對無法運作。

### 刻意分成兩份對照表

| 檔案 | 用途 | 長度上限 | 條目數 |
|---|---|---|---|
| `zh_tw.json` | 顯示名稱（`name`） | ≤ 40 字元，不含標記與換行 | 13,998 |
| `zh_tw_long.json` | 工具提示與說明文字 | ≤ 300 字元，允許標記 | 22,975 |

含有 `%1%` 的字串兩份都會排除——這類佔位符會在執行階段填入實際值，
翻譯它們會破壞輸出結果。

### 工具提示需要模糊比對

執行階段的工具提示並非 StringTable 條目的原樣。Fusion 會以 `<br><br>`
串接多個條目，且句尾標點並不一致：

| 執行階段 | StringTable |
|---|---|
| `...displays here` | `...displays here.` |
| `Generates realistic renderings of the design.<br><br>` | `Generates realistic renderings of the design.` |
| `Specifies which object types can be selected.<br><br>Use Select All to...` | 兩個獨立條目 |

`_translate_rich()` 以 `<br>` 切分，逐段翻譯，再連同分隔符原樣接回。
另有一份正規化索引，用來吸收句尾的 `.`、`:`、`。`、`：`。
若沒有任何片段查得到，該字串會維持原樣，而不會變成半中半英。

僅用完全比對時只能處理 35 條工具提示；改用片段比對後可處理 **1,161** 條。

---

## 涵蓋範圍

於 Fusion 2704.1.53、英文介面下實測：

| 區域 | 結果 |
|---|---|
| 指令名稱 | 已替換 **2,472** 項 |
| 工具提示 | 已替換 **1,161** 項 |
| 面板名稱 | 已替換 **345** 項 |
| 頁籤名稱 | 已替換 **83** 項 |
| 下拉式功能表 | 無法處理 |
| 工作區切換器 | 無法處理 |
| 對話方塊內容 | 無法處理 |
| 瀏覽器樹狀結構 | 無法處理 |
| 資料面板、首頁頁籤 | 無法處理 |

結果會是**中英混合的介面**：功能區為中文，對話方塊與瀏覽器維持英文。
安裝前請先確認這樣的取捨是否可以接受。

在 3,099 個指令定義中，有 1,443 個根本沒有工具提示，實際有內容的為 1,656 個，
因此工具提示的涵蓋率約為現有內容的 70%。

### 其餘部分為何無法處理

`API/TypeScript/@adsk/fusion/core.d.ts` 中的型別定義與實際出貨的實作並不一致。
以下皆為對執行中的產品實際探測後確認：

| `core.d.ts` 的宣告 | 實際行為 |
|---|---|
| `DropDownControl.text: string` | 屬性不存在（`AttributeError`） |
| `DropDownControl.name: string` | 讀取即拋出 `RuntimeError: InternalValidationError : nuInputControl` |
| `Workspace.tooltip` / `tooltipDescription` 可寫入 | 52 次寫入全數遭拒：*"The tooltip text displayed for the native workspaces could not be modified"* |
| `CommandDefinition.name: string` | 可寫入，原生指令亦然 |
| `Workspace.name` | 唯讀，與宣告相符 |
| `CommandInput.name` | 唯讀，與宣告相符 |

面板底下共有 570 個 `DropDownControl` 實體（另有 15,638 個 `CommandControl`
與 3,174 個 `SeparatorControl`），目標確實存在，只是無法觸及。

這兩條無效路徑仍保留在原始碼中，以 `TRY_DROPDOWN` 與 `TRY_WORKSPACE` 控制，
預設為關閉，以備日後版本開放。

**請勿只依賴 `core.d.ts` 判斷。** 務必對執行中的產品實際探測寫入行為。

### 為何僅限啟動時

在 Fusion 已經啟動完成**之後**才改寫指令定義名稱，會破壞工作區切換器：
所有項目會塌縮成同一個標籤，導致無法分辨各個工作區。
但若在啟動過程中套用相同的改寫，則完全無害。

對 2,472 筆改寫進行二分搜尋，在索引 10 找到一個觸發點——`VisibilityToggleCmd`，
其名稱為 `Show/Hide`。但僅排除它並不足夠；改寫其餘 2,470 筆仍會破壞切換器，
可見有多個彼此無關的定義各自都能單獨引發此問題。表面症狀也具誤導性：
重複出現的那個標籤其實是**另一個**指令的名稱
（`ActivateEnvironmentCommand`，其名稱正是 `Workspace`），
這是 Fusion 在無法解析真正名稱時所使用的後備值。

逐一追查所有觸發點需要多輪人工二分搜尋，卻毫無收益，因為
**切換器本來就無法翻譯**——`Workspace.name` 是唯讀的。
那裡從來就沒有可爭取的東西，唯一的要求是別把它弄壞。
將增益集限制在啟動時執行，即可確實達成這一點。

`run(context)` 會檢查 `IsApplicationStartup`，否則提前返回，不做任何變更。

---

## 安裝

### 1. 放置資料夾

將整個資料夾複製到 Fusion 的增益集目錄：

- **Windows：** `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\FusionZhTW`
- **macOS：** `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/FusionZhTW`

> **資料夾名稱必須與檔案名稱完全一致。** Fusion 是藉由在同名資料夾中尋找
> `<資料夾名稱>.manifest` 與 `<資料夾名稱>.py` 來辨識增益集。若資料夾名稱變成
> `FusionZhTW-main`——也就是 GitHub 下載 ZIP 後解壓縮的結果——增益集將不會出現在
> 對話方塊中，且**不會顯示任何錯誤訊息**。請將名稱改回 `FusionZhTW`。

Fusion 預期的結構：

```
AddIns/
└── FusionZhTW/
    ├── FusionZhTW.manifest   <- 名稱須與資料夾一致
    ├── FusionZhTW.py         <- 名稱須與資料夾一致
    ├── build_dict.py
    ├── zh_tw.json            <- 於步驟 2 產生
    └── zh_tw_long.json       <- 於步驟 2 產生
```

### 2. 產生翻譯對照表

產生器需在一般的 Python 環境執行，並非 Fusion 內建的直譯器：

```bash
python -m pip install opencc-python-reimplemented
```

```bash
python build_dict.py
```

它會自動找出最新的 `webdeploy` 版本資料夾，並將兩個 JSON 檔寫在自身所在位置。
預期輸出如下：

```
Wrote: zh_tw.json [names] 13998 entries (159 ambiguous, most frequent reading kept)
Wrote: zh_tw_long.json [descriptions] 22975 entries (214 ambiguous, most frequent reading kept)
```

若出現 `StringTable/zh-CN not found` 而中止，表示您的安裝中沒有可供轉換的
簡體中文資料，本增益集將無法運作。

### 3. 將 Fusion 的使用者語言設為 English

點選使用者圖示 → `Preferences` → `General` → `User language` → **English**，
然後重新啟動 Fusion。

這是必要步驟，並非美觀考量。對照表是以英文原文為鍵；若介面為日文或德文，
`cd.name` 會回傳該語言，導致完全無法比對。此設定儲存於您的 Autodesk 帳戶，
因此重新啟動時需要網路連線。

### 4. 執行增益集

`Utilities` → `Add-Ins` → **Add-Ins** 頁籤 → 選取 `FusionZhTW` →
勾選 **Run on Startup**，然後**重新啟動 Fusion**。

> **刻意設計為僅限啟動時套用。** 在執行期間按下 `Run` 只會顯示提示，不會有任何作用。
> 在 Fusion 已啟動的狀態下改寫指令定義名稱會破壞工作區切換器——
> 所有項目會塌縮成同一個標籤，使該選單無法使用。
> 請見[為何僅限啟動時](#為何僅限啟動時)。

執行後會以對話方塊回報替換結果。若不再需要，可在 `FusionZhTW.py` 中將
`SHOW_SUMMARY` 設為 `False` 予以隱藏；相同的統計數字一律會寫入 `last_run.log`。

### 驗證

正常執行時，回報的數字應落在以下範圍（Fusion 2704.1.53）：

```
Command names : 2472
Tooltips      : 1161
Tab names     : 83
Panel names   : 345
```

### 疑難排解

| 症狀 | 原因 |
|---|---|
| 對話方塊中找不到增益集 | 資料夾名稱與 `.py` / `.manifest` 不一致 |
| 只出現提示訊息，沒有任何變化 | 在執行期間按了 `Run`——請勾選 *Run on Startup* 並重新啟動 |
| `Translation table not found` | 略過了步驟 2，或 JSON 檔不在正確位置 |
| 所有數字皆為 0 | Fusion 的使用者語言不是 English |
| 數字遠低於參考值 | 請執行診斷腳本（見[檔案](#檔案)） |
| 功能區部分仍為英文 | 正常現象——StringTable 中沒有這些指令的條目 |

### 還原

`stop()` 會依相反順序還原它替換過的每一個字串。

除此之外，標籤屬於**執行階段狀態，從未被保存**。只要不啟用增益集重新啟動
Fusion，介面必定回復原狀——即使發生當機，或 `stop()` 執行失敗亦然。
若某項還原因物件已被銷毀而略過（工作區重建時可能發生），重新啟動即可清除。

---

## 檔案

| 檔案 | 用途 |
|---|---|
| `FusionZhTW.py` | 增益集本體 |
| `FusionZhTW.manifest` | 增益集描述檔 |
| `build_dict.py` | 對照表產生器，於 Fusion 之外執行 |
| `zh_tw.json` | 產生檔——顯示名稱 |
| `zh_tw_long.json` | 產生檔——工具提示與說明文字 |
| `last_run.log` | 每次執行時寫入各類別的統計數字 |

另有一支診斷腳本位於 `API/Scripts/FusionZhTW_diag/`。它會探測屬性是否可讀，
並嘗試寫入（使用零寬空格，且一律在 `finally` 區塊中還原），接著將控制項的
型別分布與工具提示的命中率寫入 `diag.txt`。當統計數字異常偏低時可用它排查。

請注意，該腳本的第 4 節採用完全比對，回報的工具提示命中數會遠低於增益集的
實際成果——後者使用的是片段比對。

---

## 翻譯品質

OpenCC 轉換的是字形與一般詞彙，**它並不理解 CAD 專業術語**。
`Extrude` 會被轉為 `拉伸`，這是從簡體中文版本沿用而來，未必符合台灣
CAD 業界的慣用說法。

對照表是以英文文字為鍵的純 JSON，可直接覆寫任何條目：

```json
{ "Extrude": "您偏好的術語" }
```

修正您每天實際會用到的那幾十個指令，效益遠高於整批匯入。

當同一個英文字串對應到多個簡體譯文時，採用出現頻率最高者：
名稱對照表中有 159 例，說明對照表中有 214 例。

---

## 授權——發布分支前必讀

`zh_tw.json` 與 `zh_tw_long.json` 是**衍生自 Autodesk 專有翻譯資料**，
由本機的 Fusion 安裝中擷取而來。再次散布這些檔案極可能構成授權違規。

**請只提交產生器，不要提交產生出來的對照表。** 讓每位使用者針對自己的
安裝環境執行 `build_dict.py`。

```gitignore
zh_tw.json
zh_tw_long.json
last_run.log
__pycache__/
```

本儲存庫中的程式碼為作者自行撰寫；但擷取出來的字串並非如此。

---

## 驗證環境

- Autodesk Fusion **2704.1.53**（webdeploy `61bf25b220a2d0307c84c301e65a59ac225d9a1e`）
- Windows 11 Pro
- Python 3.12.10，建置步驟使用 `opencc-python-reimplemented`

屬性的可用性因版本而異。若 Fusion 更新後統計數字歸零，請先執行診斷腳本，
再判斷是否為增益集本身的問題。
