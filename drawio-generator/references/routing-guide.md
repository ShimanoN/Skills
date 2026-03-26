# Routing & Layout Guide

---

## Layout Constants

```
X_COL0  = 300     # col0 center_x
COL_W   = 340     # column spacing  (col1 = 640, col2 = 980)
W_RECT  = 260     # rectangle node width
H_RECT  = 70      # rectangle node height
W_DIA   = 220     # diamond node width
H_DIA   = 90      # diamond node height
Y_START = 120     # y of the first node (top)
Y_GAP   = 40      # vertical gap between nodes

# Per-column left / center / right x
col0: left=170, cx=300, right=430
col1: left=510, cx=640, right=770
col2: left=850, cx=980, right=1110
```

---

## Edge Style Rule

> ⚠️ **`edgeStyle=orthogonalEdgeStyle` is FORBIDDEN.**
> The auto-router produces horizontal segments that pierce other nodes.
> **All edges must use `edgeStyle=none` with explicit Waypoints (WPs).**

---

## 5 Routing Cases

### ❶ Rightward (Yes branch: src_col < tgt_col)

Corridor x = `src_cx + W_RECT/2 + 50` (normal) or `+70` (when a fan-in bus shares the same column)

```
WPs = [(corridor_x, src_cy), (tgt_cx, src_cy)]    # Γ-shape: entry from top pin
WPs = [(corridor_x, src_cy), (corridor_x, tgt_cy)] # L-shape: entry from left pin (obstacle present)
```

Selection between Γ and L is automatic via `_gamma_clear()` obstacle check.
- **Γ-shape (top pin)**: Arrow enters the target from above. Horizontal then vertical bend.
- **L-shape (left pin)**: Arrow enters from the left. Vertical movement then horizontal bend.

col0→col1 example:
```
src_cx=300, W_RECT/2=130 → corridor_x = 300+130+50 = 480, col1 cx = 640
WPs = [(480, src_cy), (640, src_cy)]  # Γ-shape
WPs = [(480, src_cy), (480, tgt_cy)]  # L-shape
```

### ❷ Same column, downward (main flow straight line)

No WPs (straight line). Pins:
```
exitX=0.5;exitY=1  →  entryX=0.5;entryY=0
```

### ❸ Fan-in (same-column actions → shared output node)

Multiple action blocks converging on one output node.
Corridor x = `src_cx + W_RECT/2 + 40` (e.g., col1: x=810)
entryY is distributed evenly across all fan-in edges (0.2, 0.4, 0.6, 0.8, etc.)

```
WPs = [(810, src_cy), (810, tgt_cy_with_entryY_offset)]
```

### ❹ Backward loop (same column, y decreases)

Loop-back (e.g., `i++`). Routed via a left-side corridor in a U-shape.
Corridor x = `src_cx - W_RECT/2 - 50` (col0: x=120)

```
WPs = [(120, src_cy), (120, tgt_cy)]
```
Pins:
```
exitX=0;exitY=0.5  →  entryX=0;entryY=0.5
```

### ❺ Leftward (src_col > tgt_col)

Routed via left corridor: x = `src_cx - W_RECT/2 - 50`
entryY is distributed when multiple lines converge on the same target.

---

## Fan-in vs. Rightward Corridor Conflict

When a fan-in bus at x=810 (col1 right edge +40) is active,
expand the rightward Yes-branch corridor to `+70` (x=840) for 30 px clearance.

```python
_right_offset = 70 if src_col in _fanin_active_cols else 50
```

---

## RESET Hub Routing (state_machine type)

A RESET hub node is auto-generated in state machine diagrams.
- Hub position: left of col0 (`reset_x = rx - W_RESET - 50`)
- Multiple RESET edges stagger corridor_x, bypass_y, and entryY by rank to avoid overlap

```python
_r_corridor(rank) = corridor_x - rank * 15   # 195, 180, 165 ...
_r_bypass_y(rank) = bypass_y   + rank * 20   # base, base+20 ...
_r_entry_y(rank)  = (rank+1) / (n+1)         # spread around 0.5
```

---

## Verify Debugging

### 1. Reading collision output

```
⚠️  E5(S3→S9[NG]) WP(1420,735) is inside S7
```
→ WP (1420,735) of edge E5 falls inside node S7's bounding box → bypass x is too small.

### 2. Dump all edge styles & WPs

```python
import xml.etree.ElementTree as ET
tree = ET.parse("出力/07_ExiaStudio設計/drawio/08_FB_Alarm_flow.drawio")
for cell in tree.getroot().iter("mxCell"):
    if cell.get("edge") != "1": continue
    src = cell.get("source",""); tgt = cell.get("target","")
    style = cell.get("style","")
    etype = "none" if "edgeStyle=none" in style else "ORTHOGONAL!"
    wps = [(int(float(p.get("x"))),int(float(p.get("y")))) for p in cell.iter("mxPoint")]
    lbl = (cell.get("value") or "")[:20]
    print(f"  {src}->{tgt} [{lbl}] {etype} WPs={wps}")
```

### 3. Common collision causes

| Symptom | Cause | Fix |
|---------|-------|-----|
| WP falls inside another node | bypass x/y too narrow | Check `bypass_x` / `corridor_x` calculation |
| `ORTHOGONAL!` in dump | edgeStyle not set to none | Check `_pin_style()` function in script |
| Yes label overlaps adjacent edge | fan-in corridor too close to Yes corridor | Verify `_fanin_active_cols` offset (+70) is applied |
