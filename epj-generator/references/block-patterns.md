# Block XML Pattern Library

Confirmed working block structures for ExiaStudio EPJ files.  
All helpers produce Python strings with `\r\n` line endings.

### `ind` parameter quick reference

| Nesting context | `ind` to pass |
|----------------|---------------|
| Top-level `<ExiaBlocks>` (default) | `'        '` (8 sp) |
| Inside one container (InfiniteLoop / IfBlock / IfElseBlock) | `'            '` (12 sp) |
| Inside two nested containers | `'                '` (16 sp) |
| Judge sub-block helpers (`judge_*`) | use `ind + '  '` relative to outer `if_block` call |
| `kvl_get_inner` inside `var_set_block(ind='        ')` | `'          '` (10 sp = ind+2) |

---

## Variable blocks

### StandardCommentBlock

```python
def std_comment(text, ind='        '):
    return (
        f'{ind}<ExiaBlock xsi:type="StandardCommentBlock">\r\n'
        f'{ind}  <CommentValue>\r\n'
        f'{ind}    <RawValue>{text}</RawValue>\r\n'
        f'{ind}  </CommentValue>\r\n'
        f'{ind}</ExiaBlock>\r\n'
    )
```

### VariableSetBlock — constant value

```python
def var_set(value, var_no, ind='        '):
    return (
        f'{ind}<ExiaBlock xsi:type="VariableSetBlock">\r\n'
        f'{ind}  <IsBreakPoint>false</IsBreakPoint>\r\n'
        f'{ind}  <VariableValue>\r\n'
        f'{ind}    <RawValue>{value}</RawValue>\r\n'
        f'{ind}  </VariableValue>\r\n'
        f'{ind}  <SelectedVariableNo>{var_no}</SelectedVariableNo>\r\n'
        f'{ind}</ExiaBlock>\r\n'
    )
# var_set('0', 0)      -> state = 0
# var_set('True', 1)   -> result = True   NOTE: use RawValue, NOT <TrueBlock />
# var_set('False', 1)  -> result = False  NOTE: use RawValue, NOT <FalseBlock />
```

### VariableSetBlock — block output as value

```python
def var_set_block(inner_block_xml, var_no, ind='        '):
    return (
        f'{ind}<ExiaBlock xsi:type="VariableSetBlock">\r\n'
        f'{ind}  <IsBreakPoint>false</IsBreakPoint>\r\n'
        f'{ind}  <VariableValue>\r\n'
        f'{inner_block_xml}'
        f'{ind}    <RawValue>0</RawValue>\r\n'
        f'{ind}  </VariableValue>\r\n'
        f'{ind}  <SelectedVariableNo>{var_no}</SelectedVariableNo>\r\n'
        f'{ind}</ExiaBlock>\r\n'
    )
# inner_block_xml = VariableBlock / KeyValueListGetValueBlock / arithmetic block etc.
```

### VariableAddBlock — increment

```python
def var_add(value, var_no, ind='        '):
    return (
        f'{ind}<ExiaBlock xsi:type="VariableAddBlock">\r\n'
        f'{ind}  <IsBreakPoint>false</IsBreakPoint>\r\n'
        f'{ind}  <VariableValue>\r\n'
        f'{ind}    <RawValue>{value}</RawValue>\r\n'
        f'{ind}  </VariableValue>\r\n'
        f'{ind}  <SelectedVariableNo>{var_no}</SelectedVariableNo>\r\n'
        f'{ind}</ExiaBlock>\r\n'
    )
# var_add('1', 0)  -> state += 1
```

---

## Console output

### ConsoleWriteLineBlock — fixed text

```python
def console_line(text, ind='        '):
    return (
        f'{ind}<ExiaBlock xsi:type="ConsoleWriteLineBlock">\r\n'
        f'{ind}  <IsBreakPoint>false</IsBreakPoint>\r\n'
        f'{ind}  <OutputText><RawValue>{text}</RawValue></OutputText>\r\n'
        f'{ind}</ExiaBlock>\r\n'
    )
```

### ConsoleWriteLineBlock — with variable value

```python
def console_var(var_no, label, ind='        '):
    """Display: "{label}{variable_value}"
    ExiaStudio renders RawValue (label) first, then Block (variable) —
    even though Block appears before RawValue in the XML. Confirmed working.
    """
    return (
        f'{ind}<ExiaBlock xsi:type="ConsoleWriteLineBlock">\r\n'
        f'{ind}  <IsBreakPoint>false</IsBreakPoint>\r\n'
        f'{ind}  <OutputText>\r\n'
        f'{ind}    <Block xsi:type="VariableBlock">\r\n'
        f'{ind}      <SelectedVariableNo>{var_no}</SelectedVariableNo>\r\n'
        f'{ind}    </Block>\r\n'
        f'{ind}    <RawValue>{label}</RawValue>\r\n'
        f'{ind}  </OutputText>\r\n'
        f'{ind}</ExiaBlock>\r\n'
    )
# console_var(0, 'leakFlow=')  ->  output: "leakFlow=0.3"
```

---

## Flow control

### ReturnBlock

```python
def return_block(ind='        '):
    return (
        f'{ind}<ExiaBlock xsi:type="ReturnBlock">\r\n'
        f'{ind}  <IsBreakPoint>false</IsBreakPoint>\r\n'
        f'{ind}</ExiaBlock>\r\n'
    )
```

### SleepBlock

```python
def sleep_block(ms, ind='        '):
    return (
        f'{ind}<ExiaBlock xsi:type="SleepBlock">\r\n'
        f'{ind}  <IsBreakPoint>false</IsBreakPoint>\r\n'
        f'{ind}  <SleepTime><RawValue>{ms}</RawValue></SleepTime>\r\n'
        f'{ind}</ExiaBlock>\r\n'
    )
# sleep_block(1000)  -> wait 1 second
```

### IfBlock — true-only branch

```python
def if_block(inner_blocks, judge_xml, ind='        '):
    """inner_blocks: content at ind+'    ' depth
       judge_xml: a judge_* helper result"""
    return (
        f'{ind}<ExiaBlock xsi:type="IfBlock">\r\n'
        f'{ind}  <IsBreakPoint>false</IsBreakPoint>\r\n'
        f'{ind}  <Function>\r\n'
        f'{ind}    <No>0</No>\r\n'
        f'{ind}    <ExiaBlocks>\r\n'
        f'{inner_blocks}'
        f'{ind}    </ExiaBlocks>\r\n'
        f'{ind}    <IsCloseOutline>false</IsCloseOutline>\r\n'
        f'{ind}    <IsPin>false</IsPin>\r\n'
        f'{ind}  </Function>\r\n'
        f'{ind}  <Judge>\r\n'
        f'{judge_xml}'
        f'{ind}  </Judge>\r\n'
        f'{ind}</ExiaBlock>\r\n'
    )
```

### IfElseBlock — true/false branch

```python
def if_else_block(true_inner, false_inner, judge_xml, ind='        '):
    # NOTE: tag is FalseFunction, NOT ElseFunction (ElseFunction does not exist)
    return (
        f'{ind}<ExiaBlock xsi:type="IfElseBlock">\r\n'
        f'{ind}  <IsBreakPoint>false</IsBreakPoint>\r\n'
        f'{ind}  <TrueFunction>\r\n'
        f'{ind}    <No>0</No>\r\n'
        f'{ind}    <ExiaBlocks>\r\n'
        f'{true_inner}'
        f'{ind}    </ExiaBlocks>\r\n'
        f'{ind}    <IsCloseOutline>false</IsCloseOutline>\r\n'
        f'{ind}    <IsPin>false</IsPin>\r\n'
        f'{ind}  </TrueFunction>\r\n'
        f'{ind}  <FalseFunction>\r\n'
        f'{ind}    <No>0</No>\r\n'
        f'{ind}    <ExiaBlocks>\r\n'
        f'{false_inner}'
        f'{ind}    </ExiaBlocks>\r\n'
        f'{ind}    <IsCloseOutline>false</IsCloseOutline>\r\n'
        f'{ind}    <IsPin>false</IsPin>\r\n'
        f'{ind}  </FalseFunction>\r\n'
        f'{ind}  <Judge>\r\n'
        f'{judge_xml}'
        f'{ind}  </Judge>\r\n'
        f'{ind}</ExiaBlock>\r\n'
    )
```

### InfiniteLoopBlock — MAIN only

```python
def infinite_loop(inner_blocks, ind='        '):
    # inner_blocks must use ind+'    ' (4 more spaces)
    return (
        f'{ind}<ExiaBlock xsi:type="InfiniteLoopBlock">\r\n'
        f'{ind}  <IsBreakPoint>false</IsBreakPoint>\r\n'
        f'{ind}  <Function>\r\n'
        f'{ind}    <No>0</No>\r\n'
        f'{ind}    <ExiaBlocks>\r\n'
        f'{inner_blocks}'
        f'{ind}    </ExiaBlocks>\r\n'
        f'{ind}    <IsCloseOutline>false</IsCloseOutline>\r\n'
        f'{ind}    <IsPin>false</IsPin>\r\n'
        f'{ind}  </Function>\r\n'
        f'{ind}</ExiaBlock>\r\n'
    )
```

---

## Judge blocks (used inside `<Judge>` tag)

> All `judge_*` helpers return a `<Block xsi:type="...">` string, not an `<ExiaBlock>`.  
> Pass the result directly as `judge_xml` to `if_block` / `if_else_block`.  
> **Value1 must contain BOTH `<Block xsi:type="VariableBlock">` AND `<RawValue>0</RawValue>`** — omitting either causes a load error.

### TextEqualsBlock (equality)

```python
def judge_equals(var_no, value, ind='          '):
    return (
        f'{ind}<Block xsi:type="TextEqualsBlock">\r\n'
        f'{ind}  <Value1>\r\n'
        f'{ind}    <Block xsi:type="VariableBlock">\r\n'
        f'{ind}      <SelectedVariableNo>{var_no}</SelectedVariableNo>\r\n'
        f'{ind}    </Block>\r\n'
        f'{ind}    <RawValue>0</RawValue>\r\n'
        f'{ind}  </Value1>\r\n'
        f'{ind}  <Value2><RawValue>{value}</RawValue></Value2>\r\n'
        f'{ind}</Block>\r\n'
    )
# judge_equals(0, '99')  -> state == 99
```

### GreaterBlock (`>`)

```python
def judge_greater(var_no, threshold, ind='          '):
    return (
        f'{ind}<Block xsi:type="GreaterBlock">\r\n'
        f'{ind}  <Value1>\r\n'
        f'{ind}    <Block xsi:type="VariableBlock">\r\n'
        f'{ind}      <SelectedVariableNo>{var_no}</SelectedVariableNo>\r\n'
        f'{ind}    </Block>\r\n'
        f'{ind}    <RawValue>0</RawValue>\r\n'
        f'{ind}  </Value1>\r\n'
        f'{ind}  <Value2><RawValue>{threshold}</RawValue></Value2>\r\n'
        f'{ind}</Block>\r\n'
    )
```

### GreaterEqualsBlock (`>=`)

```python
def judge_gte(var_no, threshold, ind='          '):
    return (
        f'{ind}<Block xsi:type="GreaterEqualsBlock">\r\n'
        f'{ind}  <Value1>\r\n'
        f'{ind}    <Block xsi:type="VariableBlock">\r\n'
        f'{ind}      <SelectedVariableNo>{var_no}</SelectedVariableNo>\r\n'
        f'{ind}    </Block>\r\n'
        f'{ind}    <RawValue>0</RawValue>\r\n'
        f'{ind}  </Value1>\r\n'
        f'{ind}  <Value2><RawValue>{threshold}</RawValue></Value2>\r\n'
        f'{ind}</Block>\r\n'
    )
```

### LessEqualsBlock (`<=`)

```python
def judge_lte(var_no, threshold, ind='          '):
    return (
        f'{ind}<Block xsi:type="LessEqualsBlock">\r\n'
        f'{ind}  <Value1>\r\n'
        f'{ind}    <Block xsi:type="VariableBlock">\r\n'
        f'{ind}      <SelectedVariableNo>{var_no}</SelectedVariableNo>\r\n'
        f'{ind}    </Block>\r\n'
        f'{ind}    <RawValue>0</RawValue>\r\n'
        f'{ind}  </Value1>\r\n'
        f'{ind}  <Value2><RawValue>{threshold}</RawValue></Value2>\r\n'
        f'{ind}</Block>\r\n'
    )
```

### WithinRangeBlock (`MIN <= x <= MAX`)

```python
def judge_within(var_no, min_val, max_val, ind='          '):
    """Used in FB_FlowTest for OK band check."""
    return (
        f'{ind}<Block xsi:type="WithinRangeBlock">\r\n'
        f'{ind}  <Value>\r\n'
        f'{ind}    <Block xsi:type="VariableBlock">\r\n'
        f'{ind}      <SelectedVariableNo>{var_no}</SelectedVariableNo>\r\n'
        f'{ind}    </Block>\r\n'
        f'{ind}    <RawValue>0</RawValue>\r\n'
        f'{ind}  </Value>\r\n'
        f'{ind}  <MinValue><RawValue>{min_val}</RawValue></MinValue>\r\n'
        f'{ind}  <MaxValue><RawValue>{max_val}</RawValue></MaxValue>\r\n'
        f'{ind}</Block>\r\n'
    )
```

### AndJudgeBlock

```python
def judge_and(judge1_xml, judge2_xml, ind='          '):
    # NOTE: uses <Judge1>/<Judge2>, NOT <Value1>/<Value2>
    return (
        f'{ind}<Block xsi:type="AndJudgeBlock">\r\n'
        f'{ind}  <Judge1>\r\n'
        f'{judge1_xml}'
        f'{ind}  </Judge1>\r\n'
        f'{ind}  <Judge2>\r\n'
        f'{judge2_xml}'
        f'{ind}  </Judge2>\r\n'
        f'{ind}</Block>\r\n'
    )
```

### OrJudgeBlock

```python
def judge_or(judge1_xml, judge2_xml, ind='          '):
    # NOTE: uses <Judge1>/<Judge2>, NOT <Value1>/<Value2>
    return (
        f'{ind}<Block xsi:type="OrJudgeBlock">\r\n'
        f'{ind}  <Judge1>\r\n'
        f'{judge1_xml}'
        f'{ind}  </Judge1>\r\n'
        f'{ind}  <Judge2>\r\n'
        f'{judge2_xml}'
        f'{ind}  </Judge2>\r\n'
        f'{ind}</Block>\r\n'
    )
```

---

## List operations

### ListInitializeBlock

```python
def list_init(count, init_value, list_no, ind='        '):
    return (
        f'{ind}<ExiaBlock xsi:type="ListInitializeBlock">\r\n'
        f'{ind}  <IsBreakPoint>false</IsBreakPoint>\r\n'
        f'{ind}  <Value><RawValue>{init_value}</RawValue></Value>\r\n'
        f'{ind}  <Count><RawValue>{count}</RawValue></Count>\r\n'
        f'{ind}  <SelectedListNo>{list_no}</SelectedListNo>\r\n'
        f'{ind}</ExiaBlock>\r\n'
    )
# list_init(3, 0, 0)  -> doState = [0, 0, 0]
```

### ListSetElementBlock

```python
def list_set(index, value, list_no, ind='        '):
    return (
        f'{ind}<ExiaBlock xsi:type="ListSetElementBlock">\r\n'
        f'{ind}  <IsBreakPoint>false</IsBreakPoint>\r\n'
        f'{ind}  <Index><RawValue>{index}</RawValue></Index>\r\n'
        f'{ind}  <Value><RawValue>{value}</RawValue></Value>\r\n'
        f'{ind}  <SelectedListNo>{list_no}</SelectedListNo>\r\n'
        f'{ind}</ExiaBlock>\r\n'
    )
# list_set(0, 1, 0)  -> doState[0] = 1  (SOV-01 ON)
```

---

## KVL operations

### KeyValueListDeleteAllBlock (clear before mock setup)

```python
def kvl_delete_all(kvl_no, ind='        '):
    return (
        f'{ind}<ExiaBlock xsi:type="KeyValueListDeleteAllBlock">\r\n'
        f'{ind}  <IsBreakPoint>false</IsBreakPoint>\r\n'
        f'{ind}  <SelectedKeyValueListNo>{kvl_no}</SelectedKeyValueListNo>\r\n'
        f'{ind}</ExiaBlock>\r\n'
    )
```

### KeyValueListAddElementBlock (add mock data)

```python
def kvl_add(key, value, kvl_no, ind='        '):
    return (
        f'{ind}<ExiaBlock xsi:type="KeyValueListAddElementBlock">\r\n'
        f'{ind}  <IsBreakPoint>false</IsBreakPoint>\r\n'
        f'{ind}  <Key><RawValue>{key}</RawValue></Key>\r\n'
        f'{ind}  <Value><RawValue>{value}</RawValue></Value>\r\n'
        f'{ind}  <SelectedKeyValueListNo>{kvl_no}</SelectedKeyValueListNo>\r\n'
        f'{ind}</ExiaBlock>\r\n'
    )
# kvl_add('1-4', '0.3', 0)  -> mockKVL["1-4"] = 0.3
```

### KeyValueListGetValueBlock (read KVL value into variable)

Nest this inside `var_set_block()` as `inner_block_xml`:

```python
def kvl_get_inner(key, kvl_no, ind='          '):
    """Default ind='          ' (10 sp) matches var_set_block(ind='        ')"""
    return (
        f'{ind}<Block xsi:type="KeyValueListGetValueBlock">\r\n'
        f'{ind}  <Key><RawValue>{key}</RawValue></Key>\r\n'
        f'{ind}  <SelectedKeyValueListNo>{kvl_no}</SelectedKeyValueListNo>\r\n'
        f'{ind}</Block>\r\n'
    )
# Usage:
# content += var_set_block(kvl_get_inner('1-4', 0), var_no=0)
# -> leakFlow = mockKVL["1-4"]
```

---

## RT / IO-Link

### KeyValueListCopyBlock + RtxGetKVProcessDataBlock (fetch all IO-Link process data)

```python
def rtx_get_kvl(ip, kvl_no, ind='        '):
    return (
        f'{ind}<ExiaBlock xsi:type="KeyValueListCopyBlock">\r\n'
        f'{ind}  <IsBreakPoint>false</IsBreakPoint>\r\n'
        f'{ind}  <Block>\r\n'
        f'{ind}    <Block xsi:type="RtxGetKVProcessDataBlock">\r\n'
        f'{ind}      <IpAddress><RawValue>{ip}</RawValue></IpAddress>\r\n'
        f'{ind}    </Block>\r\n'
        f'{ind}  </Block>\r\n'
        f'{ind}  <SelectedKeyValueListNo>{kvl_no}</SelectedKeyValueListNo>\r\n'
        f'{ind}</ExiaBlock>\r\n'
    )
# rtx_get_kvl('192.168.1.10', 0)  -> processKVL = RT.getAllProcessData()
```

### RtxDigitalOutAllBlock (write DO list to RT unit)

```python
def rtx_do_all(ip, unit_no, list_no, ind='        '):
    return (
        f'{ind}<ExiaBlock xsi:type="RtxDigitalOutAllBlock">\r\n'
        f'{ind}  <IsBreakPoint>false</IsBreakPoint>\r\n'
        f'{ind}  <IpAddress><RawValue>{ip}</RawValue></IpAddress>\r\n'
        f'{ind}  <UnitNo><RawValue>{unit_no}</RawValue></UnitNo>\r\n'
        f'{ind}  <OutputValues>\r\n'
        f'{ind}    <Block xsi:type="VariableListBlock">'
        f'<SelectedListNo>{list_no}</SelectedListNo></Block>\r\n'
        f'{ind}  </OutputValues>\r\n'
        f'{ind}</ExiaBlock>\r\n'
    )
# rtx_do_all('192.168.1.10', 1, 0)
# -> outputs doState[0..2] to DO-001/002/011
```
