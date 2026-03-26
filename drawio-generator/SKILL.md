---
name: drawio-generator
description: "Skill for generating drawio flowcharts from JSON spec files via json_to_drawio.py. Load this skill whenever the user mentions: drawio, flowchart, state machine diagram, FB flow, json_to_drawio, routing, node layout, edge collision, verify, or drawio review — and whenever creating, modifying, or validating a drawio XML file. Covers JSON spec format, layout constants, 5 routing patterns, Yes/No edge coloring, collision verification, and design review checklists."
---

# drawio Generator

Skill for designing JSON spec files and converting them to drawio XML via `json_to_drawio.py`.
Used for **creating, modifying, and reviewing** APS flowcharts (state machine diagrams and FB flow diagrams).

---

## System Configuration

| Item | Path |
|------|------|
| Generation script | `c:\gemini\APS\Skills\aps-spec-designer\scripts\json_to_drawio.py` |
| JSON spec directory | `c:\gemini\APS\出力\07_ExiaStudio設計\json_spec\` |
| drawio output directory | `c:\gemini\APS\出力\07_ExiaStudio設計\drawio\` |
| Python runtime | `c:\gemini\APS\.venv\Scripts\python.exe` |

**Generate a single file**
```powershell
cd c:\gemini\APS
.\.venv\Scripts\python.exe Skills\aps-spec-designer\scripts\json_to_drawio.py `
  出力\07_ExiaStudio設計\json_spec\<spec>.json `
  出力\07_ExiaStudio設計\drawio\<output>.drawio
```

**Batch generate all 8 files**
```powershell
cd c:\gemini\APS
$SPEC="出力\07_ExiaStudio設計\json_spec"; $OUT="出力\07_ExiaStudio設計\drawio"
$PY=".\venv\Scripts\python.exe"; $SCR="Skills\aps-spec-designer\scripts\json_to_drawio.py"
$pairs = @(
  @("state_machine_spec.json",    "01_state_machine.drawio"),
  @("MAIN_flow_spec.json",         "02_MAIN_flow.drawio"),
  @("fb_barcode_read_spec.json",   "03_FB_BarcodeRead_flow.drawio"),
  @("fb_valve_control_spec.json",  "04_FB_ValveControl_flow.drawio"),
  @("fb_leak_test_spec.json",      "05_FB_LeakTest_flow.drawio"),
  @("fb_flow_test_spec.json",      "06_FB_FlowTest_flow.drawio"),
  @("fb_data_log_spec.json",       "07_FB_DataLog_flow.drawio"),
  @("fb_alarm_spec.json",          "08_FB_Alarm_flow.drawio")
)
foreach ($p in $pairs) { & $PY $SCR "$SPEC\$($p[0])" "$OUT\$($p[1])" 2>&1 }
```

---

## Workflow

### Step 1: Determine the Task

| User intent | Steps to follow |
|-------------|----------------|
| **Create new diagram** | Step 2 → 3 → 4 → 5 |
| **Modify existing diagram** | Read JSON spec → Step 3 → 4 → 5 |
| **Design review** | Read drawio + JSON spec → apply [Review Checklist](./references/review-checklist.md) |
| **Debug routing issue** | ET-dump drawio → refer to [Routing Guide](./references/routing-guide.md) |

### Step 2: Design the JSON Spec

→ Read **[JSON Spec Format Guide](./references/json-spec-guide.md)** first.

Key rules:
- Set `"type"` to either `"state_machine"` or `"fb_flow"`
- Spread input nodes across columns when 4 or more inputs exist
- Assign `"block_type"` to every step node
- Mark decision nodes with `"is_decision": true`
- Explicitly initialize loop counter variables (e.g., `i = 1`) in `steps`
- Always use an `IfBlock` (diamond) at loop exit — **never branch two edges out of a process node**

### Step 3: Generate & Verify

Run the script and confirm `✅ Layout verify: no collisions`.
If `⚠️ N collision(s) detected` appears → debug with [Routing Guide](./references/routing-guide.md).

### Step 4: Design Quality Check

→ Apply **[Design Review Checklist](./references/review-checklist.md)**.

### Step 5: Confirm Node/Edge Counts

```python
import xml.etree.ElementTree as ET, glob, os, re
BASE = "出力/07_ExiaStudio設計/drawio"
for fpath in sorted(glob.glob(BASE + "/*.drawio")):
    tree = ET.parse(fpath)
    nodes = [c for c in tree.getroot().iter("mxCell")
             if c.get("vertex")=="1" and c.get("id") not in ("0","1")]
    edges = [c for c in tree.getroot().iter("mxCell") if c.get("edge")=="1"]
    labels = [re.sub(r"<[^>]+>","", (e.get("value") or "")) for e in edges]
    yn = [l for l in labels if l.strip().startswith(("Yes","No"))]
    print(f"{os.path.basename(fpath)}: nodes={len(nodes)}, edges={len(edges)}, Yes/No={len(yn)}")
```

Run via: `cat <script.py> | .venv/Scripts/python.exe`

---

## Color Codes (`"color"` field)

| Value | Fill color | Use case |
|-------|-----------|----------|
| `"idle"` | Light blue `#dae8fc` | Idle state, input node, next-cycle node |
| `"action"` | Green `#d5e8d4` | Active processing state or step |
| `"transition"` | Purple `#e1d5e7` | State transition / handoff step |
| `"ok"` | Dark green | OK result output |
| `"ng"` | Pink `#f8cecc` | NG result output |
| `"alarm"` | Red `#f8cecc` + red border | Fault / EMO state |

---

## Yes/No Edge Coloring

Applied automatically by the script — no JSON spec change required.
- Edge `"label"` starting with `Yes` → **bold green**
- Edge `"label"` starting with `No` → **bold red**

---

## File Naming Conventions

| JSON spec | drawio output | Description |
|-----------|--------------|-------------|
| `state_machine_spec.json` | `01_state_machine.drawio` | MAIN state machine |
| `MAIN_flow_spec.json` | `02_MAIN_flow.drawio` | MAIN cycle flow |
| `fb_barcode_read_spec.json` | `03_FB_BarcodeRead_flow.drawio` | Barcode read FB |
| `fb_valve_control_spec.json` | `04_FB_ValveControl_flow.drawio` | Valve control FB |
| `fb_leak_test_spec.json` | `05_FB_LeakTest_flow.drawio` | Leak test FB |
| `fb_flow_test_spec.json` | `06_FB_FlowTest_flow.drawio` | Flow rate test FB |
| `fb_data_log_spec.json` | `07_FB_DataLog_flow.drawio` | Data logging FB |
| `fb_alarm_spec.json` | `08_FB_Alarm_flow.drawio` | Alarm handling FB |

New FBs follow the pattern: `fb_<name>_spec.json` → `NN_FB_<Name>_flow.drawio`
