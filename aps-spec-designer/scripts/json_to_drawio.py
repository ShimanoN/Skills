#!/usr/bin/env python3
"""
json_to_drawio.py - JSON 仕様から drawio XML を生成する
Usage: python json_to_drawio.py <input.json> <output.drawio>

type: "state_machine" | "fb_flow"
draw-guide.md の JSON フォーマットに従うこと。
"""

import json
import sys
import os
from collections import deque
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

# ── カラー定義 ──────────────────────────────────────────────────────────────
COLORS = {
    "idle":       {"fill": "#dae8fc", "stroke": "#6c8ebf"},
    "action":     {"fill": "#d5e8d4", "stroke": "#82b366"},
    "transition": {"fill": "#e1d5e7", "stroke": "#9673a6"},
    "ok":         {"fill": "#d5e8d4", "stroke": "#82b366"},
    "ng":         {"fill": "#f8cecc", "stroke": "#b85450"},
    "alarm":      {"fill": "#f8cecc", "stroke": "#b85450"},
    "default":    {"fill": "#ffffff", "stroke": "#000000"},
}

def _color(key):
    return COLORS.get(key, COLORS["default"])

def _rect_style(color_key, extra=""):
    c = _color(color_key)
    return (f"rounded=1;whiteSpace=wrap;html=1;"
            f"fillColor={c['fill']};strokeColor={c['stroke']};{extra}")

def _diamond_style(color_key="action"):
    c = _color(color_key)
    return (f"rhombus;whiteSpace=wrap;html=1;"
            f"fillColor={c['fill']};strokeColor={c['stroke']};")

def _edge_style(dashed=False, color=None):
    s = "edgeStyle=orthogonalEdgeStyle;html=1;rounded=1;"
    s += "labelBackgroundColor=#ffffff;labelBorderColor=none;"
    if dashed:
        s += "dashed=1;"
    if color:
        s += f"strokeColor={color};fontColor={color};"
    return s

def _prettify(elem):
    raw = tostring(elem, encoding="unicode")
    dom = minidom.parseString(raw)
    return dom.toprettyxml(indent="  ")

def _yn_label(label: str) -> str:
    """Yes / No ラベルの先頭を色付き太字に変換して視認性を向上させる。
    どちらの線に付いているラベルか一目でわかるようにする。
      Yes → 緑太字（#007700）
      No  → 赤太字（#aa3333）
    """
    stripped = label.lstrip()
    lower    = stripped.lower()
    if lower.startswith("yes"):
        rest = stripped[3:]
        return f"<font color='#007700'><b>Yes</b></font>{rest}"
    elif lower.startswith("no"):
        rest = stripped[2:]
        return f"<font color='#aa3333'><b>No</b></font>{rest}"
    return label

def _base_model(title, page_w="1654", page_h="1169"):
    mxfile = Element("mxfile", {"host": "app.diagrams.net"})
    diagram = SubElement(mxfile, "diagram", {"name": title})
    model = SubElement(diagram, "mxGraphModel", {
        "dx": "1422", "dy": "762",
        "grid": "1", "gridSize": "10",
        "pageWidth": page_w, "pageHeight": page_h,
        "math": "0", "shadow": "0",
    })
    root = SubElement(model, "root")
    SubElement(root, "mxCell", {"id": "0"})
    SubElement(root, "mxCell", {"id": "1", "parent": "0"})
    return mxfile, root

# ── 状態遷移図 ───────────────────────────────────────────────────────────────
def generate_state_machine(spec):
    """
    状態遷移図生成 — 完全書き直し版

    過去の反省点と対策:
      [問題1] edgeStyle=orthogonalEdgeStyle はウェイポイント指定後も auto-routing が
              動いてブロック上を通過することがある
              → 主要フロー遷移は edgeStyle=none に変更し経路を完全ピン固定する
      [問題2] COL_GAP=100px では隣列ラベルが小さすぎてブロックに重なる
              → COL_GAP=160px に拡大
      [問題3] 隣列・同Y遷移（S4→S5, S7→S9）に不要ウェイポイントを追加していた
              → edgeStyle=none + exitX=1/entryX=0 だけで水平線が確定するのでウェイポイント不要
      [問題4] 同列下向き遷移に exit/entry 制約がなかった
              → exitX=0.5;exitY=1 / entryX=0.5;entryY=0 を必ず付与する

    ルーティング方針:
      - 同列・下向き     : edgeStyle=none; exit下中央 → entry上中央 (縦線確定)
      - 隣列・同Y        : edgeStyle=none; exit右中央 → entry左中央 (横線確定)
      - 列スキップ(0→2等): edgeStyle=none; exit右 → 右端バイパス2点 → entry右 (Z字)
      - RESET            : edgeStyle=orthogonalEdgeStyle; exit左中央 → RESET_HUB (自動ルーティング)
      - セルフループ     : edgeStyle=orthogonalEdgeStyle (draw.io 自動ループ)
      - 右→左           : edgeStyle=orthogonalEdgeStyle; exit左 / entry右
    """
    title  = spec.get("title", "State Machine")
    states = spec.get("states", [])
    alarm  = spec.get("alarm")

    # ── レイアウト定数 ────────────────────────────────────────────────────
    W, H      = 220, 110
    COL_GAP   = 160          # ← 100 から拡張（ラベル用スペース確保）
    ROW_GAP   = 50
    COL_W     = W + COL_GAP  # 列中心間距離 = 380
    X_LEFT    = 220          # col0 左端（RESET_HUB 用スペース）
    Y_START   = 200
    Y_ALARM   = 40
    W_RESET   = 120
    H_RESET   = 40

    # ── col マップ・列ごとの state リスト ────────────────────────────────
    col_map    = {st["id"]: st.get("col", 0) for st in states}
    max_col    = max(col_map.values(), default=0)
    col_states = {c: [] for c in range(max_col + 1)}
    for st in states:
        col_states[col_map[st["id"]]].append(st["id"])

    # ── 各列の Y 開始: 前列→当列への最初の handoff 遷移の source Y に揃える ──
    col_y_start = {0: Y_START}
    for c in range(1, max_col + 1):
        found = False
        for tr in spec.get("transitions", []):
            sc = col_map.get(tr["from"], 0)
            tc = col_map.get(tr["to"],  -1)
            if sc == c - 1 and tc == c and tr["from"] in col_states[c - 1]:
                idx = col_states[c - 1].index(tr["from"])
                col_y_start[c] = col_y_start[c - 1] + idx * (H + ROW_GAP)
                found = True
                break
        if not found:
            col_y_start[c] = Y_START

    # ── ノード座標確定 ────────────────────────────────────────────────────
    node_xy = {}
    col_cur = dict(col_y_start)
    for st in states:
        c = col_map[st["id"]]
        node_xy[st["id"]] = (X_LEFT + c * COL_W, col_cur[c])
        col_cur[c] += H + ROW_GAP

    max_y  = max(y + H for _, y in node_xy.values())
    max_x  = max(x + W for x, _ in node_xy.values())
    page_h = str(max(1169, max_y + 300))
    page_w = str(max(1169, max_x + 300))
    mxfile, root = _base_model(title, page_w=page_w, page_h=page_h)

    # ── アラームノード（上部中央）──────────────────────────────────────────
    if alarm:
        cx = (X_LEFT + max_x) // 2
        ax = max(X_LEFT, cx - W // 2)
        # アラームノードの座標を node_xy に登録（RESET ルーティングで参照するため）
        node_xy[alarm["id"]] = (ax, Y_ALARM)
        cell = SubElement(root, "mxCell", {
            "id": alarm["id"],
            "value": (f"<b>{alarm['label']}</b>"
                      + (f"<br/><font color='#555555'><i>{alarm['sub']}</i></font>"
                         if alarm.get("sub") else "")),
            "style": _rect_style("alarm"),
            "vertex": "1", "parent": "1",
        })
        SubElement(cell, "mxGeometry", {
            "x": str(ax), "y": str(Y_ALARM),
            "width": str(W), "height": str(H), "as": "geometry",
        })
        # EMO: 個別矢印廃止 → テキスト注釈1本
        if alarm.get("from_all"):
            trigger = alarm.get("trigger", "EMO 発動")
            note = SubElement(root, "mxCell", {
                "id": "EMO_NOTE",
                "value": f"⚡ <i>{trigger}</i><br/>（任意の状態から）",
                "style": ("text;html=1;align=left;fontSize=10;"
                          "fontColor=#b85450;strokeColor=none;fillColor=none;"),
                "vertex": "1", "parent": "1",
            })
            SubElement(note, "mxGeometry", {
                "x": str(ax + W + 8), "y": str(Y_ALARM + 25),
                "width": "170", "height": "50", "as": "geometry",
            })
            # EMO_NOTE → SE 注釈エッジ（破線矢印: 右注釈から SE 右辺へ）
            e_emo = SubElement(root, "mxCell", {
                "id": "EMO_NOTE_TO_SE",
                "value": "",
                "style": ("edgeStyle=none;html=1;rounded=1;dashed=1;"
                          "strokeColor=#b85450;strokeWidth=1;"
                          "exitX=0;exitY=0.5;exitDx=0;exitDy=0;"
                          "entryX=1;entryY=0.5;entryDx=0;entryDy=0;"),
                "edge": "1", "source": "EMO_NOTE", "target": alarm["id"], "parent": "1",
            })
            SubElement(e_emo, "mxGeometry", {"relative": "1", "as": "geometry"})

    # ── 状態ノード ────────────────────────────────────────────────────────
    for st in states:
        sid  = st["id"]
        x, y = node_xy[sid]
        label = f"<b>{st['label']}</b>"
        if st.get("sub"):
            label += f"<br/><font color='#555555'><i>{st['sub']}</i></font>"
        if st.get("actions"):
            label += ("<br/><font style='font-size:10px;'>"
                      + "<br/>".join(st["actions"]) + "</font>")
        cell = SubElement(root, "mxCell", {
            "id": sid, "value": label,
            "style": _rect_style(st.get("color", "action"), "verticalAlign=top;"),
            "vertex": "1", "parent": "1",
        })
        SubElement(cell, "mxGeometry", {
            "x": str(x), "y": str(y), "width": str(W), "height": str(H),
            "as": "geometry",
        })

    # ── RESET_HUB（col0 左外側、S0 と同 Y 中央）─────────────────────────
    reset_targets = {tr["to"] for tr in spec.get("transitions", [])
                     if "RESET" in tr.get("label", "")}
    reset_node_id = None
    corridor_x     = X_LEFT - 30    # fallback（RESET_HUB 未使用時）
    hub_cy         = Y_START
    if reset_targets:
        reset_to = list(reset_targets)[0]
        rx, ry   = node_xy.get(reset_to, (X_LEFT, Y_START))
        reset_x  = rx - W_RESET - 50
        reset_y  = ry + (H - H_RESET) // 2
        # RESET入線ルーティング座標
        # ┌─────────────────────────────────────────────────────────────┐
        # │  RESET_HUB (x=50〜170, y=235〜275)                         │
        # │   右辺 x=170 の上1/4 = y=245 ← 全RESET入線はここから入る   │
        # │   右辺 x=170 の中央  = y=255 → RESET_TO_S0 はここから出る │
        # └─────────────────────────────────────────────────────────────┘
        # corridor x=195: HUB右端(170) と S0左端(220) の間 → ノードゼロ
        corridor_x   = reset_x + W_RESET + 25   # ≈ 195
        hub_top_q_y  = reset_y + H_RESET // 4   # ≈ 245 (入線用、上1/4)
        reset_node_id = "RESET_HUB"
        hub = SubElement(root, "mxCell", {
            "id": reset_node_id, "value": "RESET",
            "style": ("rounded=1;whiteSpace=wrap;html=1;"
                      "fillColor=#fff2cc;strokeColor=#d6b656;fontSize=11;fontStyle=1;"),
            "vertex": "1", "parent": "1",
        })
        SubElement(hub, "mxGeometry", {
            "x": str(reset_x), "y": str(reset_y),
            "width": str(W_RESET), "height": str(H_RESET), "as": "geometry",
        })
        # RESET_HUB → S0: edgeStyle=none で水平線
        e = SubElement(root, "mxCell", {
            "id": "RESET_TO_S0", "value": "",
            "style": ("edgeStyle=none;html=1;rounded=1;"
                      "labelBackgroundColor=#ffffff;labelBorderColor=none;"
                      "exitX=1;exitY=0.5;exitDx=0;exitDy=0;"
                      "entryX=0;entryY=0.5;entryDx=0;entryDy=0;"),
            "edge": "1", "source": reset_node_id, "target": reset_to, "parent": "1",
        })
        SubElement(e, "mxGeometry", {"relative": "1", "as": "geometry"})

    # ── 遷移矢印 ──────────────────────────────────────────────────────────
    # 系統別バイパス座標
    bypass_x    = X_LEFT + (max_col + 1) * COL_W + 60  # 列スキップ用（右端バイパス）
    bypass_y    = max_y + 80                            # RESET線用（全ノード下端バイパス）

    # ── RESET エッジ ランク割り当て（コリドー・バイパスY・entryY の行別分散用）──
    # 複数の RESET 遷移が同一 corridor_x / bypass_y / entryY=0.25 を共有すると
    # vert/horiz セグメントが完全重複する → rank 別に15px左・20px下ずつずらして回避。
    _reset_trs_list = [
        tr for tr in spec.get("transitions", [])
        if "RESET" in tr.get("label", "") and tr["from"] in node_xy
    ]
    _reset_trs_list.sort(key=lambda t: node_xy[t["from"]][1])   # src_y 昇順
    _n_reset = max(len(_reset_trs_list), 1)
    _reset_rank = {tr["from"]: k for k, tr in enumerate(_reset_trs_list)}

    def _r_corridor(rank):
        return corridor_x - rank * 15          # 195, 180, 165, ...

    def _r_bypass_y(rank):
        return bypass_y + rank * 20             # base, base+20, base+40, ...

    def _r_entry_y(rank):
        raw = (rank + 1) / (_n_reset + 1)
        # RESET_TO_S0 の exitY=0.5（中央右）と衝突する entryY=0.5 近傍を回避
        # |ey - 0.5| < 0.09 → y 差が 3px 未満で重複検出されるため 0.35/0.65 にシフト
        if abs(raw - 0.5) < 0.09:
            raw = 0.35 if raw < 0.5 else 0.65
        return raw

    # edgeStyle=none ベースの主流スタイル（ラベル背景付き）
    def _pin_style(extra="", dashed=False):
        s = ("edgeStyle=none;html=1;rounded=1;"
             "labelBackgroundColor=#ffffff;labelBorderColor=none;" + extra)
        if dashed:
            s += "dashed=1;"
        return s

    eid = 0
    for tr in spec.get("transitions", []):
        label    = tr.get("label", "")
        dashed   = tr.get("style") == "dashed"
        is_reset = "RESET" in label
        is_self  = tr["from"] == tr["to"]

        actual_tgt = reset_node_id if (is_reset and reset_node_id) else tr["to"]
        edge_label = "" if is_reset else _yn_label(label)

        src_c  = col_map.get(tr["from"], 0)
        tgt_c  = col_map.get(tr["to"],  0) if tr["to"] in col_map else -1
        src_xy = node_xy.get(tr["from"])
        tgt_xy = node_xy.get(tr["to"])

        style     = ""
        waypoints = []

        if is_self:
            # ── セルフループ ─────────────────────────────────────────────
            # orthogonalEdgeStyle に任せて draw.io が自動ループを描く
            style = _edge_style(dashed)

        elif is_reset:
            # ── RESET → RESET_HUB ───────────────────────────────────────
            # 【根本対策】orthogonalEdgeStyle の auto-routing を完全廃止。
            # edgeStyle=none + 明示ウェイポイントで経路を固定する。
            #
            # 問題の原因:
            #   S9(col2) の exitX=0(左出口) は y=1215 で水平移動 → S7(y=1160〜1270) を貫通
            #   かつ E10(S7→S9, y=1215) と重なり label を上書き
            #
            # ルーティング方針:
            #   ① RESET_HUB より上のノード(SE等): 左出口→corridor_x→hub_cy
            #   ② col0 ノード                   : 左出口→corridor_x→hub_cy
            #   ③ col1以上のノード              : 下出口→bypass_y→corridor_x→hub_cy
            #      (全ノード下端より下を通って左迂回、S7等への干渉ゼロ)
            # 【根本方針】全 RESET 線は RESET_HUB の底面中央(hub_bottom_x, hub_bottom_y)から入る
            # RESET_TO_S0 は右出口→S0左入口 (y≈255の水平線) なので、
            # 底面入口(y≈275)を使うことで経路が完全に分離される
            # ─────────────────────────────────────────────────────────────────
            # 全 RESET 入線: corridor(x=195) を通り HUB 右辺上1/4(y=245)から入る
            # RESET_TO_S0 出線: HUB 右辺中央(y=255)から出る → y が違うので重ならない
            # corridor x=195 は全 state ノード(最小 x=220) の左側 → 干渉ゼロ
            # ─────────────────────────────────────────────────────────────────
            if src_xy:
                sx, sy = src_xy
                src_mid_x = sx + W // 2
                src_bot_y = sy + H        # ノード底辺 Y
                # per-rank 座標: 複数 RESET 線を corridor/bypass/entryY で分散
                _rk  = _reset_rank.get(tr["from"], 0)
                _ck  = _r_corridor(_rk)                   # x: 195, 180, 165...
                _ey  = _r_entry_y(_rk)                    # entryY fraction
                _hub_ey = reset_y + H_RESET * _ey         # RESET_HUB右辺 entry y座標
                if sy < reset_y:
                    # ① RESET_HUB より上のノード（SE アラーム等）:
                    #    下出口 → (_ck, src_bot_y) → (_ck, _hub_ey) → HUB右辺
                    style = _pin_style(
                        f"exitX=0.5;exitY=1;exitDx=0;exitDy=0;"
                        f"entryX=1;entryY={_ey:.3f};entryDx=0;entryDy=0;"
                    )
                    waypoints = [(_ck, src_bot_y), (_ck, _hub_ey)]
                elif sx <= X_LEFT:
                    # ② col0 ノード:
                    #    左出口 → (_ck, src_mid_y) → (_ck, _hub_ey) → HUB右辺
                    src_mid_y = sy + H // 2
                    style = _pin_style(
                        f"exitX=0;exitY=0.5;exitDx=0;exitDy=0;"
                        f"entryX=1;entryY={_ey:.3f};entryDx=0;entryDy=0;"
                    )
                    waypoints = [(_ck, src_mid_y), (_ck, _hub_ey)]
                else:
                    # ③ col1 以上: 下出口 → _r_bypass_y → _ck → _hub_ey → HUB右辺
                    #    ランク別に bypass_y をずらして水平セグ重複を回避
                    _bpy = _r_bypass_y(_rk)
                    style = _pin_style(
                        f"exitX=0.5;exitY=1;exitDx=0;exitDy=0;"
                        f"entryX=1;entryY={_ey:.3f};entryDx=0;entryDy=0;"
                    )
                    waypoints = [
                        (src_mid_x, _bpy),    # 下へ（ノード外）
                        (_ck,       _bpy),    # 左へ（corridor まで）
                        (_ck,       _hub_ey), # 上へ（HUB右辺 entry y まで）
                    ]
            else:
                style = _edge_style() + "exitX=0;exitY=0.5;exitDx=0;exitDy=0;"

        elif src_c == tgt_c:
            # ── 同列遷移 ─────────────────────────────────────────────────
            if src_xy and tgt_xy:
                if tgt_xy[1] > src_xy[1]:
                    # 下向き（通常フロー）: 下出口 → 上入口 → 縦線確定
                    style = _pin_style(
                        "exitX=0.5;exitY=1;exitDx=0;exitDy=0;"
                        "entryX=0.5;entryY=0;entryDx=0;entryDy=0;",
                        dashed,
                    )
                else:
                    # 逆行（上向き）: 左バイパス、orthogonal に任せる
                    style = _edge_style(dashed) + "exitX=0;exitY=0.5;exitDx=0;exitDy=0;"
            else:
                style = _edge_style(dashed)

        elif src_c < tgt_c:
            col_diff = tgt_c - src_c
            if col_diff == 1:
                # ── 隣列遷移（同Y保証、水平線確定）────────────────────
                # edgeStyle=none + exit右中央 + entry左中央
                # → draw.io は2点を直線で結ぶだけ → 完全水平線
                # ウェイポイント不要（途中に障害物なし）
                style = _pin_style(
                    "exitX=1;exitY=0.5;exitDx=0;exitDy=0;"
                    "entryX=0;entryY=0.5;entryDx=0;entryDy=0;",
                    dashed,
                )
            else:
                # ── 列スキップ（例: col0→col2）──────────────────────────
                # 右端バイパスルート: exit右 → (bypass_x, src_y_mid) →
                #                     (bypass_x, tgt_y_mid) → entry右
                # edgeStyle=none なので各セグメントは直線 → Z字ルート
                sx, sy = src_xy
                tx, ty = tgt_xy
                waypoints = [
                    (bypass_x, sy + H // 2),
                    (bypass_x, ty + H // 2),
                ]
                style = _pin_style(
                    "exitX=1;exitY=0.5;exitDx=0;exitDy=0;"
                    "entryX=1;entryY=0.5;entryDx=0;entryDy=0;",
                    dashed,
                )

        else:
            # ── 右列→左列（SE→S0 系）────────────────────────────────────
            style = (_edge_style(dashed)
                     + "exitX=0;exitY=0.5;exitDx=0;exitDy=0;"
                     + "entryX=1;entryY=0.5;entryDx=0;entryDy=0;")

        edge = SubElement(root, "mxCell", {
            "id": f"E{eid}", "value": edge_label,
            "style": style,
            "edge": "1", "source": tr["from"], "target": actual_tgt, "parent": "1",
        })
        geo = SubElement(edge, "mxGeometry", {"relative": "1", "as": "geometry"})
        if waypoints:
            arr = SubElement(geo, "Array", {"as": "points"})
            for wx, wy in waypoints:
                SubElement(arr, "mxPoint", {"x": str(int(wx)), "y": str(int(wy))})
        eid += 1

    return _prettify(mxfile)


# ── FB フロー図 ───────────────────────────────────────────────────────────────
def generate_fb_flow(spec):
    fb_name = spec.get("fb_name", "FB")
    title = spec.get("title", fb_name)
    mxfile, root = _base_model(fb_name, page_w="1400", page_h="2400")

    W_RECT, H_RECT = 260, 70
    W_DIA,  H_DIA  = 220, 90
    X_COL0  = 300    # メイン列の中心 X
    COL_W   = 340    # 列の中心間距離
    Y_TITLE = 60
    Y_START = 120    # 最初のノード開始 Y
    Y_GAP   = 40     # ノード間の縦余白

    # ── グラフ構造の解析 ────────────────────────────────────────────────────
    adj  = {}   # from_id -> [(to_id, label)]
    radj = {}   # to_id  -> [(from_id, label)]
    for tr in spec.get("transitions", []):
        f, t, lb = tr["from"], tr["to"], tr.get("label", "")
        adj.setdefault(f, []).append((t, lb))
        radj.setdefault(t, []).append((f, lb))

    decision_ids = {s["id"] for s in spec.get("steps", []) if s.get("is_decision")}

    # ── 列割り当て（BFS）────────────────────────────────────────────────────
    # ルール：decision ノードから "yes" ラベルの辺 → col+1、それ以外 → col 維持
    node_col  = {}
    start_ids = [f"INP_{inp['name']}" for inp in spec.get("inputs", [])]
    for sid in start_ids:
        node_col[sid] = 0
    queue = deque(start_ids)
    while queue:
        nid = queue.popleft()
        col = node_col[nid]
        for to, lb in adj.get(nid, []):
            if to in node_col:
                continue
            new_col = (col + 1) if (nid in decision_ids and "yes" in lb.lower()) else col
            node_col[to] = new_col
            queue.append(to)

    # 未訪問ノードはメイン列に割り当て
    all_ids = (
        start_ids
        + [s["id"] for s in spec.get("steps", [])]
        + [o["id"] for o in spec.get("outputs", [])]
    )
    for nid in all_ids:
        node_col.setdefault(nid, 0)

    # ── JSON "col" 明示オーバーライド ──────────────────────────────────────────
    # inputs / steps / outputs に "col": N を書くと BFS 結果を上書きできる。
    # 例1: 最終 else ブロック（No フォールスルー）を col=1 に強制
    # 例2: 複数入力ノードを横並び（col=0, col=1）にして縦線干渉を回避
    for inp in spec.get("inputs", []):
        iid = f"INP_{inp['name']}"
        if "col" in inp:
            node_col[iid] = int(inp["col"])
    for s in spec.get("steps", []):
        if "col" in s:
            node_col[s["id"]] = int(s["col"])
    for o in spec.get("outputs", []):
        if "col" in o:
            node_col[o["id"]] = int(o["col"])

    # ── ノード寸法の事前定義 ─────────────────────────────────────────────────
    node_h = {}
    node_w = {}
    for inp in spec.get("inputs", []):
        iid         = f"INP_{inp['name']}"
        node_h[iid] = 55
        node_w[iid] = W_RECT
    for s in spec.get("steps", []):
        if s.get("is_decision"):
            node_h[s["id"]] = H_DIA
            node_w[s["id"]] = W_DIA
        else:
            node_h[s["id"]] = H_RECT
            node_w[s["id"]] = W_RECT
    for o in spec.get("outputs", []):
        node_h[o["id"]] = 60
        node_w[o["id"]] = W_RECT

    # ── Y 位置の計算 ──────────────────────────────────────────────────────────
    # 各ノードは「前任者の底辺 + Y_GAP」と「同列の現在カーソル」の大きい方に配置
    col_cur = {}   # col -> 次に配置可能な Y
    node_y  = {}

    def _place_y(nid):
        col   = node_col[nid]
        preds = [p for p, _ in radj.get(nid, []) if p in node_y]
        if preds:
            min_y = max(node_y[p] + node_h[p] + Y_GAP for p in preds)
        else:
            min_y = Y_START
        y = max(col_cur.get(col, Y_START), min_y)
        node_y[nid] = y
        col_cur[col] = y + node_h[nid] + Y_GAP

    for nid in start_ids:
        _place_y(nid)
    for s in spec.get("steps", []):
        _place_y(s["id"])

    # 出力ノードの Y: 同じ列に複数ある場合は縦にスタック
    base_out_y = max(col_cur.values(), default=Y_START) + 20
    outputs    = spec.get("outputs", [])
    col_out_y  = {}          # col -> 次に配置できる Y
    for o in outputs:
        oid = o["id"]
        col = node_col.get(oid, 0)
        y   = max(col_out_y.get(col, base_out_y), base_out_y)
        node_y[oid] = y
        col_out_y[col] = y + 60 + Y_GAP

    # ── セル生成 ───────────────────────────────────────────────────────────────
    # タイトル
    tc = SubElement(root, "mxCell", {
        "id": "TITLE",
        "value": f"<b>&#x25B6; {fb_name}</b><br/><i>{title}</i>",
        "style": "text;html=1;align=center;verticalAlign=middle;",
        "vertex": "1", "parent": "1",
    })
    SubElement(tc, "mxGeometry", {
        "x": str(X_COL0 - W_RECT // 2), "y": str(Y_TITLE),
        "width": str(W_RECT), "height": "40", "as": "geometry"
    })

    # 入力ノード
    for inp in spec.get("inputs", []):
        iid   = f"INP_{inp['name']}"
        cx    = X_COL0 + node_col[iid] * COL_W
        label = f"▶ {inp['name']}"
        if inp.get("key"):
            label += f'  KVL["{inp["key"]}"]'
        if inp.get("note"):
            label += f"<br/><font style='font-size:9px;' color='#666666'>{inp['note']}</font>"
        cell = SubElement(root, "mxCell", {
            "id": iid, "value": label,
            "style": _rect_style("idle", "fontSize=11;"),
            "vertex": "1", "parent": "1",
        })
        SubElement(cell, "mxGeometry", {
            "x": str(cx - W_RECT // 2), "y": str(node_y[iid]),
            "width": str(W_RECT), "height": str(node_h[iid]), "as": "geometry"
        })

    # ステップノード
    for step in spec.get("steps", []):
        sid    = step["id"]
        cx     = X_COL0 + node_col[sid] * COL_W
        is_dec = step.get("is_decision", False)
        btype  = step.get("block_type", "")
        sub    = f"<font color='#999999' style='font-size:9px;'>[{btype}]</font>" if btype else ""
        label  = step["label"].replace("\n", "<br/>") + ("<br/>" + sub if sub else "")
        if is_dec:
            style = _diamond_style("action")
            label = step["label"].replace("\n", "<br/>")
            w, h  = W_DIA, H_DIA
        else:
            style = _rect_style("action", "fontSize=11;")
            w, h  = W_RECT, H_RECT
        cell = SubElement(root, "mxCell", {
            "id": sid, "value": label,
            "style": style,
            "vertex": "1", "parent": "1",
        })
        SubElement(cell, "mxGeometry", {
            "x": str(cx - w // 2), "y": str(node_y[sid]),
            "width": str(w), "height": str(h), "as": "geometry"
        })

    # 出力ノード（列ベースの X 座標・同col縦スタック対応）
    for j, out in enumerate(outputs):
        oid   = out["id"]
        cx    = X_COL0 + node_col.get(oid, 0) * COL_W
        label = f"<b>{out['label'].replace(chr(10), '<br/>')}</b>"
        cell  = SubElement(root, "mxCell", {
            "id": oid, "value": label,
            "style": _rect_style(out.get("color", "default"), "fontSize=12;"),
            "vertex": "1", "parent": "1",
        })
        SubElement(cell, "mxGeometry", {
            "x": str(cx - W_RECT // 2), "y": str(node_y[oid]),
            "width": str(W_RECT), "height": "60", "as": "geometry"
        })

    # 遷移矢印（全エッジ edgeStyle=none + 明示 WP ルーティング）
    # ───────────────────────────────────────────────────────────────────────
    # edgeStyle=orthogonalEdgeStyle（自動ルーティング）は列をまたぐ Yes エッジで
    # 上段の col1 アクションブロックを貫通する問題があるため、全エッジを
    # edgeStyle=none + 明示 WP に統一する（state_machine と同方針）。
    #
    # ルーティング方針:
    #   ❶ 右方向（col0→col1 など）:
    #         src右センター → 列間コリドー(corridor_x) → tgt左センター
    #         WPs: [(corridor_x, src_cy), (corridor_x, tgt_cy)]
    #         corridor_x = src列の右端 + 50px（全ノードの外側）
    #   ❷ 同列下向き（No チェーン・INP→最初のノード）:
    #         底ピン → 天ピン、WP 不要（垂直線）
    #   ❸ ファンイン（同列アクション→出力ノード）:
    #         右コリドー x = 右端+40 経由、バス線収束
    #   ❹ 同列後退（ループバック）:
    #         左コリドー x = 左端-50 経由、U字折り返し
    #   ❺ 左方向（col1→col0 など）:
    #         左コリドー x 経由
    # ───────────────────────────────────────────────────────────────────────
    BASE_EDGE = (
        "edgeStyle=none;html=1;rounded=0;"
        "labelBackgroundColor=#ffffff;labelBorderColor=none;"
    )
    output_ids = {o["id"] for o in spec.get("outputs", [])}

    # 右方向エッジの順位を事前計算（同一 source から複数右方向エッジが出る場合の被り対策）
    # rank=0: Yes コリドー経由, rank>=1: 下ピン→右ルーティング
    _right_rank_tmp: dict = {}
    right_edge_rank: dict = {}
    for _i, _tr in enumerate(spec.get("transitions", [])):
        _sc = node_col.get(_tr["from"], 0)
        _tc = node_col.get(_tr["to"], 0)
        if _sc < _tc:
            right_edge_rank[_i] = _right_rank_tmp.get(_tr["from"], 0)
            _right_rank_tmp[_tr["from"]] = right_edge_rank[_i] + 1

    # 左ピンに着信がある（右方向エッジで到達される）ノードを事前収集
    # → このノードから左方向/後退エッジが出る場合、左ピン発を下ピン発に切り替えて重なりを回避
    has_incoming_at_left_pin: set = set()
    for _tr in spec.get("transitions", []):
        _sc = node_col.get(_tr["from"], 0)
        _tc = node_col.get(_tr["to"], 0)
        if _sc < _tc:  # 右方向 → tgt の左ピン(entryX=0)に着信
            has_incoming_at_left_pin.add(_tr["to"])

    # ❸ ファンイン線が存在する列を事前収集
    # → 同列に右方向エッジのコリドー(+50)が走ると fanin コリドー(+40)と 10px しか離れず
    #    ラベルが重なって見える。このため src_col が _fanin_active_cols に含まれる場合は
    #    コリドーを +70 に広げ、視覚干渉を回避する。
    _fanin_active_cols: set = set()
    for _tr in spec.get("transitions", []):
        _is, _it = _tr["from"], _tr["to"]
        if (_it in output_ids
                and node_col.get(_is, 0) == node_col.get(_it, 0)
                and _is not in decision_ids):
            _fanin_active_cols.add(node_col.get(_is, 0))

    # 左方向エッジ（src_col > tgt_col）が複数同一 target に着信する場合の対策
    # ① entry_y_spread: 同一 target への着信エッジの entryY を均等分散（水平重複回避）
    # ② left_corridor_rank: 同一 (src_col,tgt_col) ペア内で下側の src ほど
    #    コリドーを 15px 左にずらして垂直重複を回避
    _right_arrive_map: dict = {}   # tgt_id -> [edge_index, ...]
    _left_corr_counter: dict = {}  # (src_col, tgt_col) -> 次 rank
    entry_y_for_edge:  dict = {}   # edge_index -> entryY fraction (0~1)
    left_corridor_rank: dict = {}  # edge_index -> rank (0=標準, 1=左15px, ...)
    for _i, _tr in enumerate(spec.get("transitions", [])):
        _sc = node_col.get(_tr["from"], 0)
        _tc = node_col.get(_tr["to"], 0)
        if _sc > _tc:
            # ② コリドーランク（遷移リスト順で同一ペアの何番目か）
            _key = (_sc, _tc)
            left_corridor_rank[_i] = _left_corr_counter.get(_key, 0)
            _left_corr_counter[_key] = left_corridor_rank[_i] + 1
            # ① entry_y 分散のために target をカウント
            _right_arrive_map.setdefault(_tr["to"], []).append(_i)
    # entry_y を均等配分
    for _tgt, _eidxs in _right_arrive_map.items():
        _n = len(_eidxs)
        for _k, _idx in enumerate(_eidxs):
            entry_y_for_edge[_idx] = (_k + 1) / (_n + 1)

    # ❸ ファンイン: 同一出力ノードに複数アクションが収束する場合の entryY 分散
    # 全エッジが entryY=0.5 だと最終水平セグメントが完全重複する → 均等分散で回避
    _fanin_map: dict = {}   # output_id -> [edge_index]
    for _i, _tr in enumerate(spec.get("transitions", [])):
        _tid = _tr["to"]
        _sid = _tr["from"]
        if (_tid in output_ids
                and node_col.get(_sid, 0) == node_col.get(_tid, 0)
                and _sid not in decision_ids):
            _fanin_map.setdefault(_tid, []).append(_i)
    fanin_entry_y: dict = {}   # edge_index -> entryY fraction
    for _tgt, _eidxs in _fanin_map.items():
        _n = len(_eidxs)
        if _n > 1:
            for _k, _idx in enumerate(_eidxs):
                fanin_entry_y[_idx] = (_k + 1) / (_n + 1)

    for i, tr in enumerate(spec.get("transitions", [])):
        src_id  = tr["from"]
        tgt_id  = tr["to"]
        src_col = node_col.get(src_id, 0)
        tgt_col = node_col.get(tgt_id, 0)
        src_cx  = X_COL0 + src_col * COL_W
        tgt_cx  = X_COL0 + tgt_col * COL_W
        src_cy  = node_y.get(src_id, 0) + node_h.get(src_id, 70) / 2
        tgt_cy  = node_y.get(tgt_id, 0) + node_h.get(tgt_id, 70) / 2
        waypoints = []

        if (tgt_id in output_ids
                and src_col == tgt_col
                and src_id not in decision_ids):
            # ❸ ファンイン: 右コリドー経由で出力ノードへ収束
            # 複数エッジが同一出力ノードに収束する場合は entryY を均等分散して
            # 最終水平セグメントの重複を回避する
            corridor_x = src_cx + W_RECT // 2 + 40
            _fey = fanin_entry_y.get(i, 0.5)
            tgt_pin_y = node_y[tgt_id] + node_h.get(tgt_id, 60) * _fey
            waypoints  = [(corridor_x, src_cy), (corridor_x, int(tgt_pin_y))]
            pins = (
                f"exitX=1;exitY=0.5;exitDx=0;exitDy=0;"
                f"entryX=1;entryY={_fey:.3f};entryDx=0;entryDy=0;"
            )

        elif src_col < tgt_col:
            if right_edge_rank.get(i, 0) == 0:
                # ❶ 右方向 1本目（Yes 分岐）
                # 優先: Γ字（上ピン入線）= exit右 → コリドーx → tgt列中心 → tgt天ピン
                # フォールバック: L字（左ピン入線）= コリドーを左に下ろして tgt左ピンへ
                # フォールバック条件: Γ経路（水平セグ at src_cy、垂直セグ at tgt_cx）が
                #   他のノードと干渉する場合
                _right_offset = 70 if src_col in _fanin_active_cols else 50
                corridor_x = src_cx + W_RECT // 2 + _right_offset
                _tgt_top   = node_y[tgt_id]

                def _gamma_clear():
                    for _nid, _ny in node_y.items():
                        if _nid in (src_id, tgt_id): continue
                        _nw = node_w.get(_nid, W_RECT)
                        _nh = node_h.get(_nid, H_RECT)
                        _ncx = X_COL0 + node_col.get(_nid, 0) * COL_W
                        _nx = _ncx - _nw / 2
                        _nr = _ncx + _nw / 2
                        _nb = _ny + _nh
                        # 水平セグ: y=src_cy, x=corridor_x→tgt_cx
                        if (_ny < src_cy < _nb
                                and _nx < max(corridor_x, tgt_cx)
                                and _nr > min(corridor_x, tgt_cx)):
                            return False
                        # 垂直セグ: x=tgt_cx, y=src_cy→_tgt_top
                        if (_nx < tgt_cx < _nr
                                and _ny < _tgt_top
                                and _nb > src_cy):
                            return False
                    return True

                if _gamma_clear():
                    # Γ字: 上ピン入線（どのノードに入るか一目で分かる）
                    waypoints = [(corridor_x, src_cy), (tgt_cx, src_cy)]
                    pins = (
                        "exitX=1;exitY=0.5;exitDx=0;exitDy=0;"
                        "entryX=0.5;entryY=0;entryDx=0;entryDy=0;"
                    )
                else:
                    # L字フォールバック: コリドーを左に下ろして左ピン入線
                    waypoints = [(corridor_x, src_cy), (corridor_x, tgt_cy)]
                    pins = (
                        "exitX=1;exitY=0.5;exitDx=0;exitDy=0;"
                        "entryX=0;entryY=0.5;entryDx=0;entryDy=0;"
                    )
            else:
                # ❶' 右方向 2本目以降（No→col1 など）: 下ピン→右ルーティング
                # src 下端から真下に降りて tgt の y で折れ右へ → Yes コリドーと被らない
                waypoints = [(src_cx, tgt_cy)]
                pins = (
                    "exitX=0.5;exitY=1;exitDx=0;exitDy=0;"
                    "entryX=0;entryY=0.5;entryDx=0;entryDy=0;"
                )

        elif src_col > tgt_col:
            # ❺ 左方向: 左コリドーで L 字 2-WP ルーティング
            # ② コリドーランクに応じて x を左にずらして垂直重複を回避
            _rank = left_corridor_rank.get(i, 0)
            corridor_x = src_cx - W_RECT // 2 - 50 - _rank * 15
            # ① entryY を分散（複数エッジが同一 tgt に着信する場合）
            ey = entry_y_for_edge.get(i, 0.5)
            tgt_pin_y = node_y[tgt_id] + node_h.get(tgt_id, H_RECT) * ey
            if src_id in has_incoming_at_left_pin:
                # 右方向エッジが左ピンに着信済み → 左ピン発だと水平セグが重なる
                # → 下ピン発に切り替えて重なりを回避
                bottom_y  = node_y[src_id] + node_h.get(src_id, H_RECT)
                waypoints = [(corridor_x, bottom_y), (corridor_x, tgt_pin_y)]
                pins = (
                    f"exitX=0.5;exitY=1;exitDx=0;exitDy=0;"
                    f"entryX=1;entryY={ey:.3f};entryDx=0;entryDy=0;"
                )
            else:
                waypoints = [(corridor_x, src_cy), (corridor_x, tgt_pin_y)]
                pins = (
                    f"exitX=0;exitY=0.5;exitDx=0;exitDy=0;"
                    f"entryX=1;entryY={ey:.3f};entryDx=0;entryDy=0;"
                )

        else:
            # 同列
            if tgt_cy < src_cy:
                # ❹ 後退（ループバック）: 左コリドーで U 字折り返し
                corridor_x = src_cx - W_RECT // 2 - 50
                if src_id in has_incoming_at_left_pin:
                    # 左ピン着信あり → 下ピン発で回避
                    bottom_y  = node_y[src_id] + node_h.get(src_id, H_RECT)
                    waypoints = [(corridor_x, bottom_y), (corridor_x, tgt_cy)]
                    pins = (
                        "exitX=0.5;exitY=1;exitDx=0;exitDy=0;"
                        "entryX=0;entryY=0.5;entryDx=0;entryDy=0;"
                    )
                else:
                    waypoints = [(corridor_x, src_cy), (corridor_x, tgt_cy)]
                    pins = (
                        "exitX=0;exitY=0.5;exitDx=0;exitDy=0;"
                        "entryX=0;entryY=0.5;entryDx=0;entryDy=0;"
                    )
            else:
                # ❷ 同列下向き（No チェーン）: 底→天 ピン、WP 不要
                pins = (
                    "exitX=0.5;exitY=1;exitDx=0;exitDy=0;"
                    "entryX=0.5;entryY=0;entryDx=0;entryDy=0;"
                )

        edge = SubElement(root, "mxCell", {
            "id": f"TE{i}", "value": _yn_label(tr.get("label", "")),
            "html": "1",
            "style": BASE_EDGE + pins,
            "edge": "1", "source": src_id, "target": tgt_id, "parent": "1",
        })
        geo = SubElement(edge, "mxGeometry", {"relative": "1", "as": "geometry"})
        if waypoints:
            arr = SubElement(geo, "Array", {"as": "points"})
            for wx, wy in waypoints:
                SubElement(arr, "mxPoint", {"x": str(int(wx)), "y": str(int(wy))})

    return _prettify(mxfile)


# ── メイン ───────────────────────────────────────────────────────────────────
# ── レイアウト自動検証 ───────────────────────────────────────────────────────
def _seg_crosses_box(p1, p2, bx, by, bw, bh, margin=4):
    """水平 or 垂直の線分がノードBBOX内部を通過するか。edgeStyle=none 専用。"""
    x1, y1 = p1; x2, y2 = p2
    if abs(y1 - y2) < 1:          # 水平線分
        y = y1; xmin, xmax = min(x1, x2), max(x1, x2)
        return (by + margin < y < by + bh - margin) \
            and xmax > bx + margin and xmin < bx + bw - margin
    if abs(x1 - x2) < 1:          # 垂直線分
        x = x1; ymin, ymax = min(y1, y2), max(y1, y2)
        return (bx + margin < x < bx + bw - margin) \
            and ymax > by + margin and ymin < by + bh - margin
    return False  # 斜め線は対象外


def verify_drawio(path):
    """生成した drawio ファイルのレイアウトを検証。エッジ経路がノードBBOXを
    貫通していないかセグメント単位でチェックし、問題を標準出力へ報告する。"""
    import xml.etree.ElementTree as ET
    tree = ET.parse(path)

    # ── ノード収集 ──────────────────────────────────────────────────
    nodes = {}
    for cell in tree.getroot().iter("mxCell"):
        geo = cell.find("mxGeometry")
        if geo is None or cell.get("vertex") != "1":
            continue
        nid = cell.get("id", "")
        if nid in ("0", "1"):
            continue
        nodes[nid] = (
            float(geo.get("x", 0)), float(geo.get("y", 0)),
            float(geo.get("width", 0)), float(geo.get("height", 0)),
        )

    # ── ピン座標を style 文字列から算出するヘルパー ──────────────────
    def _pin_pos(nid, style, prefix):
        """exitX/exitY または entryX/entryY からピクセル座標を返す。"""
        if nid not in nodes:
            return None
        nx, ny, nw, nh = nodes[nid]
        parts = {}
        for s in style.split(";"):
            if "=" not in s:
                continue
            k, v = s.split("=", 1)
            try:
                parts[k] = float(v)
            except ValueError:
                pass
        rx = parts.get(f"{prefix}X", 0.5)
        ry = parts.get(f"{prefix}Y", 0.5)
        return (nx + nw * rx, ny + nh * ry)

    # ── エッジ収集（ピン→WP→ピン の全セグメントをチェック） ──────────
    issues = []
    for cell in tree.getroot().iter("mxCell"):
        if cell.get("edge") != "1":
            continue
        eid   = cell.get("id", "?")
        label = (cell.get("value") or "")[:24]
        src   = cell.get("source", "")
        tgt   = cell.get("target", "")
        style = cell.get("style", "")
        skip  = {src, tgt, "0", "1"}   # 接続先は干渉判定から除外

        wps = [(float(p.get("x", 0)), float(p.get("y", 0)))
               for p in cell.iter("mxPoint")]

        # 完全パス: src出口ピン → WP列 → tgt入口ピン
        src_pin = _pin_pos(src, style, "exit")
        tgt_pin = _pin_pos(tgt, style, "entry")
        full_path = []
        if src_pin:
            full_path.append(src_pin)
        full_path.extend(wps)
        if tgt_pin:
            full_path.append(tgt_pin)

        if len(full_path) < 2:
            continue

        for i in range(len(full_path) - 1):
            seg_a, seg_b = full_path[i], full_path[i + 1]
            for nid, (nx, ny, nw, nh) in nodes.items():
                if nid in skip:
                    continue
                if _seg_crosses_box(seg_a, seg_b, nx, ny, nw, nh):
                    issues.append(
                        f"  ⚠️  E{eid}({src}→{tgt}[{label}]) "
                        f"seg({seg_a[0]:.0f},{seg_a[1]:.0f})→"
                        f"({seg_b[0]:.0f},{seg_b[1]:.0f}) "
                        f"が {nid} を貫通"
                    )

        # WP 自体がノード内にある場合も検出
        for (px, py) in wps:
            for nid, (nx, ny, nw, nh) in nodes.items():
                if nid in skip:
                    continue
                if nx + 4 < px < nx + nw - 4 and ny + 4 < py < ny + nh - 4:
                    issues.append(
                        f"  ⚠️  E{eid}({src}→{tgt}[{label}]) "
                        f"WP({px:.0f},{py:.0f}) が {nid} の内部"
                    )

    if issues:
        print(f"\n🔍 Layout verify: {len(issues)} 件の干渉を検出 ({path})")
        for msg in issues:
            print(msg)
    else:
        print(f"✅ Layout verify: 干渉なし ({path})")
    return issues


def main():
    if len(sys.argv) < 3:
        print("Usage: json_to_drawio.py <input.json> <output.drawio>")
        sys.exit(1)

    input_path  = sys.argv[1]
    output_path = sys.argv[2]

    with open(input_path, "r", encoding="utf-8") as f:
        spec = json.load(f)

    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    dtype = spec.get("type", "state_machine")
    if dtype == "state_machine":
        xml = generate_state_machine(spec)
    elif dtype == "fb_flow":
        xml = generate_fb_flow(spec)
    else:
        raise ValueError(f"Unknown type: {dtype}. Use 'state_machine' or 'fb_flow'.")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(xml)

    print(f"✅ Generated: {output_path}")
    verify_drawio(output_path)


if __name__ == "__main__":
    main()
