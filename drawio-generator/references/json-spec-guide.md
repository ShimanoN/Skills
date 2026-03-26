# JSON Spec Format Guide

---

## State Machine (`"type": "state_machine"`)

```json
{
  "type": "state_machine",
  "title": "APS Inspector — MAIN State Machine",
  "states": [
    {
      "id": "S0",
      "label": "STATE_IDLE (0)",
      "sub": "Standby",
      "actions": ["Confirm barcode", "Wait for START"],
      "color": "idle",
      "col": 0
    },
    {
      "id": "S4",
      "label": "STATE_TRANSITION (4)",
      "sub": "①→② handoff (safety step)",
      "actions": ["⚠ EV-BYP fully open first", "Required before MFC ramp-up"],
      "color": "transition",
      "col": 0
    },
    {
      "id": "S8",
      "label": "STATE_RESULT_OK (8)",
      "sub": "Inspection passed",
      "actions": ["FB_DataLog(OK)", "OK lamp ON", "SOV-01=OFF"],
      "color": "ok",
      "col": 1
    }
  ],
  "transitions": [
    {"from": "S0", "to": "S1",  "label": "START pressed\n& barcode read"},
    {"from": "S0", "to": "S0",  "label": "Barcode not read", "style": "dashed"},
    {"from": "S8", "to": "S0",  "label": "RESET"},
    {"from": "SE", "to": "S0",  "label": "RESET (after safety check)"}
  ],
  "alarm": {
    "id": "SE",
    "label": "STATE_ALARM (E)",
    "sub": "Emergency stop — all valves closed",
    "trigger": "DI-001 EMO triggered",
    "from_all": true
  }
}
```

### `alarm.from_all: true` behavior
- SE node is placed at the top of the diagram
- An annotation text block and a **dashed arrow from annotation → SE** are auto-generated (T3 fix applied)
- The `SE → S0` RESET transition must still be declared explicitly in `transitions`

---

## FB Flow (`"type": "fb_flow"`)

```json
{
  "type": "fb_flow",
  "fb_name": "FB_LeakTest",
  "title": "① Leak Test — Measure & Judge",
  "inputs": [
    {"name": "KVL", "key": "1-4", "note": "IL-004 flow meter A-16"}
  ],
  "steps": [
    {
      "id": "B2",
      "block_type": "VariableSetBlock",
      "label": "leakFlow = flow_convert( KVL[\"1-4\"] )\n(implemented with ReturnValueBlock)"
    },
    {
      "id": "D1",
      "block_type": "IfBlock",
      "label": "leakFlow > LEAK_THRESHOLD ?\n(▲ set after Q33 is confirmed)",
      "is_decision": true
    }
  ],
  "outputs": [
    {"id": "O_NG", "label": "result = False (NG)\n→ STATE_RESULT_NG (9)", "color": "ng"},
    {"id": "O_OK", "label": "result = True (OK)\n→ STATE_TRANSITION (4)",  "color": "ok"}
  ],
  "transitions": [
    {"from": "INP_KVL", "to": "B2"},
    {"from": "B2",      "to": "D1"},
    {"from": "D1",      "to": "O_NG", "label": "Yes (leak detected)"},
    {"from": "D1",      "to": "O_OK", "label": "No (normal)"}
  ]
}
```

---

## Field Reference

### `inputs[]`

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Input variable name. Node ID becomes `INP_<name>` |
| `note` | string | Small description text shown inside the node |
| `key` | string | IO-Link key (e.g., `"1-4"`). Displayed inside the node |
| `col` | int | Column (default: 0). **Must be distributed for 4+ inputs** |

> ⚠️ **When 4+ input nodes all share col=0, edges from upper inputs to B1 pierce through lower input nodes.**
> Distribute to col=1 / col=2 to avoid this.

### `steps[]`

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique node ID |
| `block_type` | string | ExiaStudio block type (see table below) |
| `label` | string | Display text. Use `\n` for newlines |
| `is_decision` | bool | `true` renders the node as a diamond (IfBlock) |
| `col` | int | Overrides BFS column assignment (use only when needed) |

### `outputs[]`

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique node ID |
| `label` | string | Description of the output state |
| `color` | string | `ok` / `ng` / `alarm` / `idle` / `action` |
| `col` | int | Column (default: determined by BFS) |

### `transitions[]`

| Field | Type | Description |
|-------|------|-------------|
| `from` | string | Source node ID (`INP_xxx` also valid) |
| `to` | string | Target node ID |
| `label` | string | Edge label. Starts with `Yes`/`No` for auto color-coding |
| `style` | string | `"dashed"` for dashed line |

---

## ExiaBlock Type Reference

| block_type | Purpose |
|------------|---------|
| `KeyValueListCopyBlock` | Bulk-read all IO-Link data into a KVL |
| `VariableSetBlock` | Assign / compute / call a function |
| `IfBlock` | Conditional branch (`is_decision: true` → diamond) |
| `InfiniteLoopBlock` | Infinite loop (main cycle) |
| `ListInitializeBlock` | Initialize a list |
| `ListSetElementBlock` | Set a list element |
| `ExcelOpenBlock` | Open an Excel file |
| `ExcelWriteListBlock` | Write a list to Excel |
| `ExcelSetCellBlock` | Write a value to a specific cell |
| `RtxISDUHexWriteBlock` | ISDU write (device initialization) |
| `ReturnValueBlock` | Return a function value |
| `VariableAddBlock` | Increment a variable |
| `RtxDIReadBlock` | Read a digital input (DI) |
| `RtxDOWriteBlock` | Write a digital output / solenoid valve [requires CKD confirmation T1] |

---

## Loop Pattern — Correct vs. Wrong

**Never** branch two edges from a process node. Always use an `IfBlock` (`is_decision: true`) for loop exit.

✅ **Correct**
```json
{"from": "B6",    "to": "D_LOOP"},
{"from": "D_LOOP","to": "B4",  "label": "Yes (continue)"},
{"from": "D_LOOP","to": "D2",  "label": "No (all done)"}
```

❌ **Wrong** (two edges from a process node)
```json
{"from": "B6", "to": "B4", "label": "i < 25 (continue)"},
{"from": "B6", "to": "D2", "label": "i == 25 (all done)"}
```

Also: always initialize loop variables explicitly in `steps` (e.g., add `i = 1` to the label of the init step).

---

## FB Design Conventions

### KVL Acquisition Strategy (MAIN bulk-read model)

When MAIN_flow step C2 performs a `KeyValueListCopyBlock` bulk read:
- Each FB receives the KVL as `INP_KVL` — **do not re-acquire KVL inside the FB**
- Start the FB at B2 (value extraction), not B1 (KVL acquisition)

```json
"inputs": [{"name": "KVL", "key": "1-4", "note": "..."}],
"steps": [
  {"id": "B2", "block_type": "VariableSetBlock", "label": "leakFlow = flow_convert( KVL[\"1-4\"] )"},
  ...
],
"transitions": [
  {"from": "INP_KVL", "to": "B2"},
  ...
]
```

### `count` (Excel row counter) Management

Manage `count++` in **one place only** — inside FB_DataLog's `VariableAddBlock`.
Adding a separate `count++` step in MAIN_flow causes double-increment in the same cycle.

### DI Read Block Placement

Insert `RtxDIReadBlock` immediately before any `IfBlock` that references a DI value.
In polling-based designs, add an explicit read block (e.g., `B_DI003_READ`) just before `D_RESET`.
