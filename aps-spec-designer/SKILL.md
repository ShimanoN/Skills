---
name: aps-spec-designer
description: "APSタワー検査装置の ExiaStudio 実装仕様書・drawio フロー図を生成するスキル。「ExiaStudio」「フロー図」「FB設計」「実装仕様書」「状態遷移」「drawio」「検査シーケンス」「プログラム設計」「aps-spec」のいずれかに言及されたとき、または APSタワー検査装置の ExiaStudio 実装コードの設計・仕様定義が必要な場面ではすべてこのスキルを使うこと。APS 固有の IO-Link キーマップ・バルブ真理表・FB 定義・drawio 生成スクリプトを内包する。"
---

# APS Spec Designer

APSタワー検査装置の ExiaStudio 実装に向けた **状態遷移図・FB フロー図・FB仕様書** を生成するスキル。

## 出力ファイル一覧

| 出力物 | 形式 | 内容 |
|-------|------|------|
| `MAIN_state_machine.drawio` | drawio XML | STATE 0〜SE の状態遷移図 |
| `FB_XXX_flow.drawio` | drawio XML (FB毎) | 各 FB の内部フロー（ExiaBlock タイプ注釈付き）|
| `ExiaStudio_FB仕様書.md` | Markdown | FB 入出力・変数定義・処理ロジック・実装メモ |

**出力先：** `C:\gemini\APS\出力\07_ExiaStudio設計\`（なければ自動作成）

---

## 作業手順

### Step 1: コンテキスト読み込み（必須）
必ず最初に [`references/aps-context.md`](references/aps-context.md) を読む。  
IO-Link キーマップ・バルブ真理表・判定条件がある。

### Step 2: スコープ確認
ユーザーが「全部」「状態遷移のみ」「FB: XXX のみ」のどれを求めているか確認する。  
明示がない場合は「全部（状態遷移 + 全 FB + 仕様書）」を生成する。

### Step 3: drawio 生成
[`references/draw-guide.md`](references/draw-guide.md) を読み、JSON spec を設計して `scripts/json_to_drawio.py` で変換する。

```bash
cd "C:\gemini\APS"
.venv\Scripts\python.exe Skills\aps-spec-designer\scripts\json_to_drawio.py ^
  出力\07_ExiaStudio設計\state_machine_spec.json ^
  出力\07_ExiaStudio設計\MAIN_state_machine.drawio
```

### Step 4: FB 仕様書生成
[`references/fb-guide.md`](references/fb-guide.md) を読み、全 FB の仕様書を Markdown で生成する。

---

## 命名規則（ハイブリッド）

| 種別 | 規則 | 例 |
|------|------|----|
| 関数（FB）名 | 英語 PascalCase + `FB_` プレフィックス | `FB_LeakTest`, `FB_FlowTest` |
| 変数名 | 日本語または英語（わかりやすさ優先） | `漏れ流量`, `flowRate` |
| 定数名 | 英語 UPPER_SNAKE | `FLOW_TARGET`, `LEAK_THRESHOLD` |
| STATE 名 | 英語 SCREAMING_SNAKE + 整数値 | `STATE_IDLE (0)`, `STATE_LEAK_FILL (1)` |
| IO-Link Key | `"ユニット番号-ポート番号"` 形式 | `"1-4"` = ILU-A / CH4 |

---

## 標準 STATE 一覧（APS 検査メインフロー）

| No | STATE 名 | アクション概要 |
|----|----------|--------------|
| 0 | `STATE_IDLE` | 待機。バーコード読取確認・START 待ち |
| 1 | `STATE_LEAK_FILL` | SOV-01=ON / EV-BYP=閉 / EV-OUT=閉 / EPC=テスト圧設定 |
| 2 | `STATE_LEAK_STABILIZE` | タイマー待機（3〜5 秒）|
| 3 | `STATE_LEAK_MEASURE` | 流量計 A-16（IL-004, Key="1-4"）計測・閾値判定 |
| 4 | `STATE_TRANSITION` | **EV-BYP 先行全開**（MFC 昇流前の必須ステップ）|
| 5 | `STATE_FLOW_FILL` | EV-OUT=開 / EPC=流量検査圧切替 / MFC=60 L/min 指令 |
| 6 | `STATE_FLOW_STABILIZE` | タイマー待機（3〜5 秒）|
| 7 | `STATE_FLOW_MEASURE` | FSM3×25（IL-005〜IL-029）全スロット計測・判定 |
| 8 | `STATE_RESULT_OK` | 結果記録・OK 表示・ランプ・SOV-01=OFF |
| 9 | `STATE_RESULT_NG` | 結果記録・NG 表示・ブザー×3・SOV-01=OFF |
| E | `STATE_ALARM` | EMO 発動・全弁強制閉（任意 STATE から遷移）|

> ⚠️ **STATE_TRANSITION（4） が最重要安全ステップ。**  
> EV-BYP を先行開放してから MFC を昇流する順序を守らないと、  
> 流量計 A-16 に 60 L/min が通過して破損するリスクがある。

---

## 標準 FB 一覧

| FB 名 | 担当処理 | 主要 IO-Link Key |
|-------|---------|-----------------|
| `FB_BarcodeRead` | バーコード読取・ロット ID 取得 | `"4-8"`（IL-030）|
| `FB_ValveControl` | STATE に応じた電磁弁 3 台制御 | DO-001/002/011 |
| `FB_LeakTest` | ①漏れ流量計測・閾値判定 | `"1-4"`（IL-004）|
| `FB_FlowTest` | ②FSM3×25 全スロット計測・判定 | `"1-5"`〜`"4-7"`（IL-005〜029）|
| `FB_DataLog` | 検査結果を Excel に記録 | ExcelWriteBlock |
| `FB_Alarm` | EMO・異常処理 | DI-001 |

詳細は [`references/fb-guide.md`](references/fb-guide.md) を参照。

---

## MAIN の骨格（FB を組み合わせる構造）

```
MAIN:
  [初期化]
    ExcelOpen(ダッシュボード.xlsx)
    ISDU初期設定: RtxISDUHexWriteBlock（FSM3 測定モード設定）
    state = STATE_IDLE (0)
    
  [InfiniteLoop] ← ここからがメインサイクル
    1. EMO チェック → FB_Alarm（毎サイクル最優先）
    2. KeyValueListCopy（192.168.1.10 → KVL 全データ一括取得）
    3. FB_BarcodeRead(KVL["4-8"]) → lotID, isRead
    4. IfBlock (state) でシーケンス分岐:
         state==0 → START 待ち（isRead チェック）
         state==1 → FB_ValveControl(1)  充填
         state==2 → タイマー
         state==3 → FB_LeakTest(KVL["1-4"])  判定→state 分岐
         state==4 → FB_ValveControl(4)  EV-BYP 先行開放
         state==5 → FB_ValveControl(5)  MFC 昇流
         state==6 → タイマー
         state==7 → FB_FlowTest(KVL)  判定→state 分岐
         state==8 → FB_DataLog(OK)  OK 表示
         state==9 → FB_DataLog(NG)  NG 表示・ブザー
```

---

## Skill② との接続

このスキルが生成する `ExiaStudio_FB仕様書.md` が **Skill② `exiastudio-impl`** の入力になる。  
FB 仕様書の「ExiaBlock」欄は CKD 技術確認（T1〜T3）待ちの項目を `[要確認]` タグで明示すること。
