---
name: epj-generator
description: "ExiaStudio の EPJ プログラムファイルを生成するスキル。「EPJ を作って」「ExiaStudio プログラムを生成」「FB_XXX の .epj」「InfiniteLoop」「IfElseBlock」「VariableSetBlock」「ConsoleWriteLine」「KVL」「RtxDigitalOutAll」「block を書いて」などと言われたとき、または APS 検査装置の ExiaStudio プログラム実装が必要な場面では必ずこのスキルを使うこと。ExiaStudio EPJ XML の生成ルール・確定済みブロック構造・アンチパターン・Python スクリプト生成ワークフローを内包する。"
---

# EPJ Generator

Generates ExiaStudio `.epj` files (XML) via a Python script — **never write XML by hand, always generate a script and run it.**

| Path | Pattern |
|------|---------|
| Generator script | `C:\gemini\APS\スクリプト\_gen_<name>.py` |
| EPJ output | `C:\gemini\APS\プログラム\<Name>_test.epj` |

---

## Step 0 — Pre-flight

Before writing a single line of XML output:

1. Read the relevant existing EPJ or `仕様書/仕様書_Draft.md` to fix variable / KVL / List **numbers** (No.0, No.1 …).
2. Verify every string value in an `<ExiaBlocks>` will produce **zero `<RawValue />`** (empty self-closing tag) — this is an instant load failure in ExiaStudio.
3. Mark any provisional values (key names, state values, thresholds) with `# TODO:` comments in the script.

---

## Step 1 — Script skeleton

```python
CRLF = '\r\n'

# --- build XML body ---
content = ''
content += std_comment('...')
content += var_set('0', 0)
# ... etc.

# --- assemble & write ---
out_path = r'C:\gemini\APS\プログラム\FB_XXX_test.epj'
xml_str = EPJ_HEADER + content + EPJ_FOOTER

with open(out_path, 'w', encoding='utf-8', newline='\r\n') as f:
    f.write(xml_str.replace('\r\n', '\n'))   # prevent double-CRLF

print(f'Written: {out_path}')
print(f'  size (LF): {len(xml_str.replace(chr(13), ""))} bytes')
```

`EPJ_HEADER`, `EPJ_FOOTER` and all declaration patterns → [`references/epj-structure.md`](references/epj-structure.md)

---

## Step 2 — Indentation levels

The `ind` parameter of every helper function must match the **nesting depth** in the output XML.

| Context | `ind` value | spaces |
|---------|-------------|--------|
| Top-level `<ExiaBlocks>` | `'        '` | 8 |
| Inside `InfiniteLoopBlock / IfBlock / IfElseBlock` → `<ExiaBlocks>` | `'            '` | 12 |
| Inside a second-level block (e.g. IfBlock inside InfiniteLoop) | `'                '` | 16 |
| Judge sub-block (`judge_equals` etc.) | `ind + '  '` (2 more than the containing block) | — |

Passing the wrong `ind` only affects readability, not correctness — ExiaStudio ignores whitespace — but keeping it consistent makes diffs readable.

---

## Step 3 — Anti-patterns (hard failures)

| ❌ WRONG | ✅ CORRECT |
|---------|----------|
| `<RawValue />` empty self-closing tag | `<RawValue>value</RawValue>` — always a value |
| `<TrueBlock />` or `<FalseBlock />` inside `<VariableValue>` | `<RawValue>True</RawValue>` / `<RawValue>False</RawValue>` |
| `IfBlock` + `<ElseFunction>` tag | `IfElseBlock` + `<FalseFunction>` (ElseFunction does not exist) |
| `Value1` in judge block with only `<RawValue>0</RawValue>` | Must have **both** `<Block xsi:type="VariableBlock">` **and** `<RawValue>0</RawValue>` inside `Value1` |
| `AndJudgeBlock` / `OrJudgeBlock` with `<Value1>/<Value2>` | Use **`<Judge1>/<Judge2>`** — these blocks do NOT use Value1/Value2 |
| BOM-encoded UTF-8 | `encoding='utf-8'` — never `utf-8-sig` |

---

## Step 4 — Validate

```powershell
py "C:\gemini\APS\スクリプト\_gen_<name>.py"
py "C:\gemini\APS\スクリプト\_chk_all_epj.py"
```

The checker reports `RawValue/=N` — **must be 0** before handing off to ExiaStudio.

---

## Block index

Full Python helper functions → [`references/block-patterns.md`](references/block-patterns.md)

| Block type | Helper | Purpose |
|-----------|--------|--------|
| `StandardCommentBlock` | `std_comment` | In-program comment label |
| `VariableSetBlock` (literal) | `var_set` | Assign constant to variable |
| `VariableSetBlock` (block output) | `var_set_block` | Assign computed value to variable |
| `VariableAddBlock` | `var_add` | Increment variable |
| `IfBlock` | `if_block` | If-only branch |
| `IfElseBlock` | `if_else_block` | If/else branch |
| `InfiniteLoopBlock` | `infinite_loop` | Infinite loop (MAIN) |
| `SleepBlock` | `sleep_block` | Fixed delay (ms) |
| `ReturnBlock` | `return_block` | Early return from function |
| `ConsoleWriteLineBlock` (literal) | `console_line` | Console output, fixed text |
| `ConsoleWriteLineBlock` (variable) | `console_var` | Console output with variable value |
| `ListInitializeBlock` | `list_init` | Fill list with constant value |
| `ListSetElementBlock` | `list_set` | Set one list element |
| `KeyValueListDeleteAllBlock` | `kvl_delete_all` | Clear KVL (mock setup) |
| `KeyValueListAddElementBlock` | `kvl_add` | Add KVL entry (mock setup) |
| `KeyValueListGetValueBlock` | `kvl_get_inner` | Read KVL value (nested in `var_set_block`) |
| `KeyValueListCopyBlock` + `RtxGetKVProcessDataBlock` | `rtx_get_kvl` | Fetch IO-Link process data into KVL |
| `RtxDigitalOutAllBlock` | `rtx_do_all` | Write DO list to RT unit |
| `TextEqualsBlock` | `judge_equals` | Equality comparison (Judge) |
| `GreaterBlock` | `judge_greater` | Greater-than comparison (Judge) |
| `GreaterEqualsBlock` | `judge_gte` | Greater-or-equal comparison (Judge) |
| `LessEqualsBlock` | `judge_lte` | Less-or-equal comparison (Judge) |
| `WithinRangeBlock` | `judge_within` | Range check MIN≤x≤MAX (Judge) |
| `AndJudgeBlock` | `judge_and` | AND of two Judge blocks |
| `OrJudgeBlock` | `judge_or` | OR of two Judge blocks |

---

## APS-specific notes

- **state variable** = Var No.0 (`state`): 0=idle, 1–3=leak, 4=transition, 5–7=flow, 8=OK, 9=NG, 99=alarm (E)
- **doState list** = List No.0: `[0]`=SOV-01 (DO-001), `[1]`=EV-OUT (DO-002), `[2]`=EV-BYP (DO-011)
- **IO-Link KVL key format**: `"unit-port"` e.g. `"1-4"` = ILU-A/CH4 = flow meter A-16
- **RT IP address**: `192.168.1.10` (demo unit; confirm for real hardware)
- **Provisional DI key names** (pending Q9 resolution): `"DI-001"` (EMO), `"DI-003"` (RESET) — mark with `# TODO:`
| `KeyValueListGetValueBlock` | KVL からキーで値取得 |
| `KeyValueListDeleteAllBlock` | KVL 全削除（mock 用）|
| `KeyValueListAddElementBlock` | KVL 要素追加（mock 用）|
| `RtxDigitalOutAllBlock` | DO 一括出力 |
| `TextEqualsBlock` | 文字列・数値等値比較（Judge 内）|
| `GreaterBlock` | 大なり比較（Judge 内）|
| `GreaterEqualsBlock` | 以上比較（Judge 内）|
| `WithinRangeBlock` | 範囲内判定（Judge 内）|
| `AndJudgeBlock` / `OrJudgeBlock` | 複合条件（Judge 内）|

---

## APS 固有の設計メモ

- **state 変数**は変数 No.0（`state`）。値: 0=待機, 1〜3=漏れ試験, 4=遷移, 5〜7=流量試験, 8=結果OK, 9=結果NG, 99=アラーム(E)
- **doState** は List No.0: `[0]=SOV-01(DO-001), [1]=EV-OUT(DO-002), [2]=EV-BYP(DO-011)`
- **IO-Link KVL キー形式**: `"ユニット番号-ポート番号"` 例: `"1-4"` = ILU-A/CH4 = 流量計A-16
- **RT IP アドレス**: `192.168.1.10`（デモ機）
- **DI キー名**は Q9 解消まで仮値（`"DI-001"`, `"DI-003"` 等）を使い `# TODO:` を付ける
