# FB 設計ガイド（aps-spec-designer 参照ファイル）

## 命名規則まとめ（ハイブリッド）

| 種別 | 規則 | 例 |
|------|------|----|
| 関数（FB）名 | 英語 PascalCase + `FB_` | `FB_LeakTest`, `FB_FlowTest` |
| 変数名 | 日本語 or 英語（わかりやすさ優先）| `漏れ流量`, `flowRate[1]` |
| 定数名 | 英語 UPPER_SNAKE | `FLOW_TARGET = 2.4`, `FLOW_MIN = 2.28` |
| STATE 変数 | 整数 + コメント | `state = 0  # STATE_IDLE` |
| リスト名 | 日本語 or 英語 | `FSM3計測値[]`, `slotFlows[]` |
| KVL 参照 | `"ユニット-ポート"` 文字列 | `KVL["1-4"]` |

---

## FB 定義一覧

### FB_BarcodeRead

```
目的    : バーコードリーダーからロット ID を取得し、START インターロックを制御
入力    : KVL（KeyValueList）
読取先  : KVL["4-8"]（IL-030 SICK IO-Link バーコードリーダー）
出力    : lotID（文字列）, isRead（bool）
処理フロー :
  1. KeyValueListCopyBlock  ← KVL 取得
  2. VariableSetBlock  lotID = KVL["4-8"]
  3. IfBlock  lotID != "" → isRead = True / else → isRead = False
  4. ReturnValueBlock  {lotID, isRead}
インターロック :
  MAIN の STATE_IDLE でバーコード未読取（isRead=False）の場合は START を受け付けない
ExiaBlock : ReturnValueBlock（Arg1 = KVL["4-8"]）
```

---

### FB_ValveControl

```
目的    : STATE 値に基づき電磁弁 3 台（SOV-01/EV-OUT/EV-BYP）を制御
入力    : state（整数）
出力    : なし（RtxDOWriteBlock で直接 DO 出力）
処理フロー :
  IfBlock  state == 0         → SOV-01=OFF, EV-OUT=OFF, EV-BYP=OFF  （待機）
  IfBlock  state == 1,2,3     → SOV-01=ON,  EV-OUT=OFF, EV-BYP=OFF  （①漏れ試験）
  IfBlock  state == 4         → SOV-01=ON,  EV-OUT=OFF, EV-BYP=ON   （⚠ 先行開放）
  IfBlock  state == 5,6,7     → SOV-01=ON,  EV-OUT=ON,  EV-BYP=ON   （②流量検査）
  IfBlock  state == 8 or 9    → SOV-01=OFF, EV-OUT=OFF, EV-BYP=OFF  （結果表示）
  IfBlock  state == E(alarm)  → SOV-01=OFF, EV-OUT=OFF, EV-BYP=OFF  （EMO）
⚠ 最重要 :
  state==4（STATE_TRANSITION）で EV-BYP を先行開放する処理が安全上最重要。
  このブロックが先に呼ばれてから MAIN が MFC 指令を出す順序を守ること。
ExiaBlock : RtxDOWriteBlock（[要確認 T1] CKD 技術確認待ち）
```

---

### FB_LeakTest

```
目的    : ①漏れ試験の流量計測と OK/NG 判定
入力    : KVL（KeyValueList）
読取先  : KVL["1-4"]（IL-004 流量計 A-16）
出力    : result（bool）, leakFlow（float, L/min）
処理フロー :
  1. KeyValueListCopyBlock  ← KVL 取得
  2. VariableSetBlock  leakFlow = 流量値換算( KVL["1-4"] )
     ※ 流量値換算 は ReturnValueBlock 関数（サンプル .epj に実装例あり）
  3. IfBlock  leakFlow > LEAK_THRESHOLD
        Yes → result = False（NG）
        No  → result = True（OK）
  4. ReturnValueBlock  {result, leakFlow}
定数    : LEAK_THRESHOLD（Q33 欠陥定義確定後に設定。それまでは仮置き）
ExiaBlock : ReturnValueBlock（Arg1 = KVL["1-4"]）
注意    : EV-BYP が閉じていることが前提（全量が A-16 経由）
```

---

### FB_FlowTest

```
目的    : ②流量検査 FSM3×25 全スロット計測と OK/NG 判定
入力    : KVL（KeyValueList）
出力    : result（bool）, failedSlots（リスト）, slotFlows（リスト 25 要素）
処理フロー :
  1. KeyValueListCopyBlock  ← KVL 取得
  2. 各スロット（1〜25）ごとに:
       slotFlows[i] = 流量値換算( KVL[SLOT_KEYS[i]] )
       IfBlock  slotFlows[i] < FLOW_MIN OR slotFlows[i] > FLOW_MAX
           → failedSlots に i を追加
  3. IfBlock  failedSlots.length == 0
        → result = True（全スロット OK）
        → result = False（NG スロットあり）
  4. ReturnValueBlock  {result, failedSlots, slotFlows}
定数    :
  FLOW_TARGET = 2.4       （L/min、確定）
  FLOW_MIN    = 2.28      （L/min、±5% 下限、確定）
  FLOW_MAX    = 2.52      （L/min、±5% 上限、確定）
SLOT_KEYS（1〜25 → KVL キー対応）: aps-context.md を参照
ExiaBlock : ReturnValueBlock（Arg1=KVL）
注意    :
  ExiaStudio でのループ処理（For 相当）の実装方法は [要確認] 。
  リスト × 25 の ListSetElementBlock を手動展開する可能性あり。
  → drawio で「ループ処理（要 Skill② 確認）」と注釈すること。
```

---

### FB_DataLog

```
目的    : 検査結果を Excel ファイルに記録
入力    : lotID（文字列）, testType（"①" or "②"）, result（bool）,
          measureValues（リスト）, timestamp（文字列）
出力    : なし
処理フロー :
  1. ExcelSetCellBlock  日付 → 指定セル
  2. ExcelSetCellBlock  ロット ID → 指定セル
  3. ExcelSetCellBlock  検査結果（OK/NG）→ 指定セル
  4. ExcelWriteListBlock  計測値リスト → 行方向に書き込み
  5. VariableAddBlock  行カウンタ++ （次回記録行をずらす）
ファイル : ダッシュボード.xlsx（MAIN の初期化で ExcelOpenBlock 済み）
ExiaBlock : ExcelOpenBlock, ExcelSetCellBlock, ExcelWriteListBlock, VariableAddBlock
```

---

### FB_Alarm

```
目的    : EMO 検出・異常停止処理
入力    : DI-001（EMO NC 接点、RTシリーズ DI 経由）
出力    : なし（FB_ValveControl(E) を MAIN から呼び出す形）
処理フロー :
  1. IfBlock  DI-001 == OFF（NC 接点が開く = EMO 押下）
       → MAIN に state = STATE_ALARM をセット
       → FB_ValveControl(E)  全弁強制閉
       → アラームランプ ON（DO-008）
       → ブザー×3 パターン（タイマー制御）[要確認]
実装方針 :
  EMO チェックは InfiniteLoop の先頭で毎サイクル実施（ポーリング方式）。
  EMO 発動後は RESET ボタン（DI-003）待ちに遷移→ STATE_IDLE に戻る。
ExiaBlock : RtxDIReadBlock [要確認 T1], IfBlock
```

---

## MAIN の構造テンプレート（ExiaStudio 実装イメージ）

```
■ MAIN 関数
  [初期化ブロック群]
    ExcelOpenBlock         ← ダッシュボード.xlsx を開く
    RtxISDUHexWriteBlock   ← FSM3 初期設定（ISDU書込み）
    VariableSetBlock       ← state = 0 (STATE_IDLE)
    VariableSetBlock       ← count = 1
    
  [InfiniteLoopBlock]  ← ここからメインサイクル
    ┌─ EMO チェック（最優先）
    │   IfBlock DI-001 OFF → FB_Alarm
    │
    ├─ KeyValueListCopyBlock  ← 全 IO-Link データ一括取得
    │
    ├─ FB_BarcodeRead(KVL) → lotID, isRead
    │
    ├─ state による分岐（IfBlock の連鎖）
    │   IfBlock state==0 → START & isRead チェック → state=1
    │   IfBlock state==1 → FB_ValveControl(1) → state=2
    │   IfBlock state==2 → タイマー待機 [要確認] → state=3
    │   IfBlock state==3 → FB_LeakTest(KVL) → result で state=4 or 9
    │   IfBlock state==4 → FB_ValveControl(4) → state=5 ← ⚠ BYP 先行
    │   IfBlock state==5 → FB_ValveControl(5) + MFC 指令 → state=6
    │   IfBlock state==6 → タイマー待機 [要確認] → state=7
    │   IfBlock state==7 → FB_FlowTest(KVL) → result で state=8 or 9
    │   IfBlock state==8 → FB_DataLog(OK) → OK 表示 → state=0
    │   IfBlock state==9 → FB_DataLog(NG) → NG 表示・ブザー → state=0
    │
    └─ ExcelSetCellBlock  ← 行カウンタ更新
```

---

## Skill② への引き継ぎ項目

| 項目 | 内容 | CKD 確認番号 |
|------|------|------------|
| DO 制御ブロック名 | `RtxDOWriteBlock`（仮称）の正式名と使い方 | T1 |
| タイマーブロック | 安定待機（3〜5 秒）の実装方法 | — |
| ループ処理 | FSM3×25 の繰り返し計測実装 | — |
| DI 読取ブロック | EMO（DI-001）の読取方法 | T1 |
| MFC 指令ブロック | 流量値の書き込み方法（IL-002 出力）| T2 |
