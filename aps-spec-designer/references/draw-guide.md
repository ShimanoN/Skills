# drawio 生�Eガイド！Eps-spec-designer 参�Eファイル�E�E

## 概要E

drawio 生�Eは 2 スチE��プ！E

1. **AI ぁEJSON spec を設計�E出力すめE*�E�このガイドに従う�E�E
2. **スクリプトぁEdrawio XML に変換する**

```bash
cd "C:\gemini\APS"
.venv\Scripts\python.exe Skills\aps-spec-designer\scripts\json_to_drawio.py ^
  <input.json> <output.drawio>
```

---

## 色コード！E"color"` フィールドに持E��！E

| color 値 | 意味 | 使ぁE��ころ |
|---------|------|----------|
| `"idle"` | 水色 | 征E���E初期状慁E|
| `"action"` | 緁E| 処琁E��行中の状慁E|
| `"transition"` | 紫 | 刁E��・移行スチE��チE|
| `"ok"` | 緑（濁E��| OK 結果 |
| `"ng"` | 薁E�� | NG 結果 |
| `"alarm"` | 赤 | 異常・EMO |

---

## ① 状態�E移図 JSON spec フォーマッチE

```json
{
  "type": "state_machine",
  "title": "APS検査裁E�� MAIN 状態�E移図",
  "states": [
    {
      "id": "S0",
      "label": "STATE_IDLE (0)",
      "sub": "征E��中",
      "actions": ["バ�Eコード確誁E, "START 征E��"],
      "color": "idle"
    },
    {
      "id": "S1",
      "label": "STATE_LEAK_FILL (1)",
      "sub": "①漏れ試騁E允E��",
      "actions": ["SOV-01=ON", "EV-BYP=閁E, "EV-OUT=閁E, "EPC=チE��ト圧"],
      "color": "action"
    },
    {
      "id": "S4",
      "label": "STATE_TRANSITION (4)",
      "sub": "①→② 移衁E,
      "actions": ["⚠ EV-BYP 先行�E閁E, "�E�EFC昁E��前に忁E��！E],
      "color": "transition"
    },
    {
      "id": "S8",
      "label": "STATE_RESULT_OK (8)",
      "sub": "検査 OK",
      "actions": ["結果記録", "OK ランチE],
      "color": "ok"
    },
    {
      "id": "S9",
      "label": "STATE_RESULT_NG (9)",
      "sub": "検査 NG",
      "actions": ["結果記録", "NG ランチE, "ブザーÁE"],
      "color": "ng"
    }
  ],
  "transitions": [
    {"from": "S0", "to": "S1", "label": "START 押下\n& バ�Eコード読取渁E},
    {"from": "S0", "to": "S0", "label": "バ�Eコード未読叁E, "style": "dashed"},
    {"from": "S1", "to": "S2", "label": "允E��完亁E},
    {"from": "S3", "to": "S8", "label": "漏れ流E�� ≤ 閾値�E�EK�E�E},
    {"from": "S3", "to": "S9", "label": "漏れ流E�� > 閾値�E�EG�E�E},
    {"from": "S8", "to": "S0", "label": "RESET"},
    {"from": "S9", "to": "S0", "label": "RESET"}
  ],
  "alarm": {
    "id": "SE",
    "label": "STATE_ALARM (E)",
    "sub": "異常停止",
    "trigger": "DI-001 EMO 発勁E,
    "from_all": true
  }
}
```

---

## ② FB フロー図 JSON spec フォーマッチE

```json
{
  "type": "fb_flow",
  "fb_name": "FB_LeakTest",
  "title": "①漏れ試騁E計測・判宁E,
  "inputs": [
    {"name": "KVL", "key": "1-4", "note": "流E��訁EA-16�E�EL-004�E�E}
  ],
  "steps": [
    {
      "id": "B1",
      "block_type": "KeyValueListCopyBlock",
      "label": "IO-Link チE�Eタ取得\nKVL ↁE192.168.1.10"
    },
    {
      "id": "B2",
      "block_type": "VariableSetBlock",
      "label": "漏れ流E�� = 流E��値換算\n( KVL[\"1-4\"] )"
    },
    {
      "id": "D1",
      "block_type": "IfBlock",
      "label": "漏れ流E�� > LEAK_THRESHOLD ?",
      "is_decision": true
    }
  ],
  "outputs": [
    {"id": "O_OK", "label": "result = OK\n�E�次スチE�Eトへ�E�E, "color": "ok"},
    {"id": "O_NG", "label": "result = NG\n�E�ETATE_RESULT_NG へ�E�E, "color": "ng"}
  ],
  "transitions": [
    {"from": "B1", "to": "B2"},
    {"from": "B2", "to": "D1"},
    {"from": "D1", "to": "O_NG",  "label": "Yes�E�漏れあり�E�E},
    {"from": "D1", "to": "O_OK",  "label": "No�E�正常�E�E}
  ]
}
```

---

## ExiaBlock タイプ注釈一覧�E�Elock_type に使ぁE���E�E

サンプル `.epj` から確認済みのブロチE��タイプ！E

| block_type | 用送E|
|------------|------|
| `KeyValueListCopyBlock` | IO-Link 全チE�EタめEKVL に一括取征E|
| `VariableSetBlock` | 変数への代入�E�計算�E関数呼び出し含む�E�|
| `IfBlock` | 条件刁E��E|
| `InfiniteLoopBlock` | 無限ループ（メインサイクル�E�|
| `ListInitializeBlock` | リスト�E期化 |
| `ListSetElementBlock` | リスト�E要素を設宁E|
| `ExcelOpenBlock` | Excel ファイルをオープン |
| `ExcelWriteListBlock` | リストを Excel に書き込み |
| `ExcelSetCellBlock` | 持E��セルに値を書き込み |
| `RtxISDUHexWriteBlock` | ISDU 書き込み�E�デバイス初期設定）|
| `ReturnValueBlock` | 関数の戻り値を返す |
| `VariableAddBlock` | 変数にインクリメンチE|

CKD 技術確認！E1�E�征E��の未確認ブロチE���E�E

| block_type�E�仮�E�| 用送E| 確認状慁E|
|----------------|------|---------|
| `RtxDOWriteBlock`�E�仮称�E�| DO 出力（電磁弁EON/OFF�E�| **[要確誁ET1]** |
| タイマ�EブロチE���E�仮称�E�| 安定征E��タイマ�E | **[要確認]** |
| ループカウンタブロチE�� | FSM3ÁE5 ループ�E琁E| **[要確認]** |

> `[要確認]` ブロチE��を使ぁE��E��は drawio 注釈欁E�� `⚠ Skill② 確認征E��` と記載すること、E

---

## ③ 褁E��入力ノード�E配置ルール�E�重要E��E

> ⚠�E�E**同じノ�Eドに雁E��E��れる入力が 2 個以上ある場合、`"col"` で横並び配置が忁E��、E*  
> 全入力が col=0 に縦スタチE��されると、上�E入力�E雁E��E�Eへの直線が下�E入力ノードを貫通する、E

### 問題ケース�E�EB_DataLog: 5入力が全て col=0�E�E

```
INP_lotID     (col0, y=120) ──━E ↁEこ�E直線が
INP_testType  (col0, y=215) ──┤     INP_testType〜INP_timestamp を貫送E⚠�E�E
INP_result    (col0, y=310) ──┤
INP_measures  (col0, y=405) ──┤
INP_timestamp (col0, y=500) ──┴──▶ B1(col0, y=595)
```

### 解決筁E `"col"` で横刁E��

```json
"inputs": [
  {"name": "lotID",         "col": 1},
  {"name": "testType",      "col": 2},
  {"name": "result",        "col": 1},
  {"name": "measureValues", "col": 2},
  {"name": "timestamp"}
]
```

ↁE同一 col に最大 2 個まで、縦間隔に余裕を持たせる、E

### 配置ルール�E�目安！E

| 入力数 | 推奨配置 |
|-------|---------|
| 1 | col=0 のみ |
| 2、E | col=0 に雁E��E��縦間隔が小さければ col=1 へ刁E���E�|
| 4 以丁E| **忁E�� col 刁E��**。col=0 / col=1 に交互�E置 |

> 入力にめE`"col"` オーバ�Eライドが使える�E�Eteps/outputs と同仕様）、E

---

## ④ エチE��ルーチE��ング原則�E�重要E��E

> ⚠�E�E**`edgeStyle=orthogonalEdgeStyle` は使用禁止、E*  
> drawio の自動ルーターは水平セグメントが他ノードを貫通するバグを起こす、E 
> **全エチE��めE`edgeStyle=none` + 明示 WP�E�Eaypoint�E�で制御すること、E*

### レイアウト定数�E�Egenerate_fb_flow()` 冁E��E

```
X_COL0 = 300      # col0 center_x
COL_W  = 340      # 列間隁EↁEcol1 center_x = 640, col2 center_x = 980
W_RECT = 260      # 矩形ノ�Eド幁E
H_RECT = 70       # 矩形ノ�Eド高さ
W_DIA  = 220      # 菱形ノ�Eド幁E
H_DIA  = 90       # 菱形ノ�Eド高さ
Y_START = 120     # 最初�Eノ�EチEcenter_y
Y_GAP   = 40      # ノ�Eド間ギャチE�E

# colN の左端 / 右端
col0_left  = X_COL0 - W_RECT//2 = 170
col0_right = X_COL0 + W_RECT//2 = 430
col1_left  = 640 - W_RECT//2    = 510
col1_right = 640 + W_RECT//2    = 770
```

### 5 種類�EルーチE��ングケース

| ケース | 条件 | コリド�E x | ピン |
|-------|------|-----------|------|
| ❶ 右方向！Ees刁E��！E| src_col < tgt_col | `src_cx + W_RECT//2 + 50`�E�Eol0→col1 なめE**x=480**�E�E| exit右 ↁEentry左 |
| ❷ 同�E下向ぁE| src_col == tgt_col, 前進 | なし（直線！E| exitX=0.5;exitY=1 ↁEentryX=0.5;entryY=0 |
| ❸ ファンイン�E�アクション→�E力！E| 同�E or 右、�E力ノードへ | `src_cx + W_RECT//2 + 40`�E�Eol1 なめE**x=810**�E�E| exit右 ↁEentry右�E�バス合流E��E|
| ❹ 後退ループ（同列！E| src_col == tgt_col, y が後退 | `src_cx - W_RECT//2 - 50`�E�Eol0 なめE**x=120**�E�E| exit左 ↁEentry左 U孁E|
| ❺ 左方吁E| src_col > tgt_col | `src_cx - W_RECT//2 - 50` | exit左 ↁEentry右 |

**WP の形式（❶ 右方向�E例）！E*
```
WPs = [(480, src_cy), (480, tgt_cy)]
ↁEsrc 右端 ↁEコリド�E x=480 で垂直移勁EↁEtgt 左端
```

**なぁEx=480 が安�Eか！E*
- col0 右端 = 430, col1 左端 = 510 ↁEx=480 はそ�E中間�E空白帯
- どのノ�Eド�E bounding box にもかからなぁE

---

## ④ JSON spec での列�E置オーバ�EライチE

BFS が�E動割り当てする列を強制変更したぁE��合、`steps` また�E `outputs` の要素に `"col": N` を追加する、E

```json
{
  "id": "B89",
  "block_type": "RtxDOWriteBlock",
  "label": "SOV-01=OFF, ...",
  "col": 1
}
```

**ユースケース�E�E*
- No チェーンが長く、Yes 刁E���Eのノ�Eドが BFS で col0 に配置されてしまぁE��吁E
- 出力ノードを特定�Eに固定したい場吁E

---

## ⑤ 生�E後�E干渉チェチE���E�Eerify�E�E

生�Eした drawio ファイルは忁E��以下で干渉確認を行う�E�E

```powershell
cd c:\gemini\APS
.venv\Scripts\python.exe -c "
import xml.etree.ElementTree as ET
tree = ET.parse('出劁E07_ExiaStudio設訁Edrawio/<ファイル吁E.drawio')
print('=== 全エチE��のスタイル + WP ===')
for cell in tree.getroot().iter('mxCell'):
    if cell.get('edge') != '1': continue
    src = cell.get('source',''); tgt = cell.get('target','')
    style = cell.get('style','')
    edge_type = 'none' if 'edgeStyle=none' in style else 'ORTHOGONAL!'
    wps = [(int(float(p.get('x'))), int(float(p.get('y')))) for p in cell.iter('mxPoint')]
    lbl = (cell.get('value') or '')[:10]
    print(f'  {src}->{tgt}  [{lbl}]  {edge_type}  WPs={wps}')
"
```

**チェチE��ポイント！E*
- `ORTHOGONAL!` ぁE1 件でも�Eたら問題あめEↁEスクリプト修正が忁E��E
- WP の x 座標がコリド�E篁E��冁E��Eol0右端〜col1左端�E�に収まってぁE��か確誁E

---

## スクリプト実行例（�E手頁E��E

```bash
# Step 1: JSON spec を生成！EI ぁEout/ に書き�Eす！E
# 侁E C:\gemini\APS\出力\07_ExiaStudio設訁Estate_machine_spec.json

# Step 2: drawio XML に変換
cd "C:\gemini\APS"
.venv\Scripts\python.exe Skills\aps-spec-designer\scripts\json_to_drawio.py ^
  出力\07_ExiaStudio設訁Estate_machine_spec.json ^
  出力\07_ExiaStudio設訁EMAIN_state_machine.drawio

# FB フロー図�E�例！E
.venv\Scripts\python.exe Skills\aps-spec-designer\scripts\json_to_drawio.py ^
  出力\07_ExiaStudio設訁Efb_leak_test_spec.json ^
  出力\07_ExiaStudio設訁EFB_LeakTest_flow.drawio
```
