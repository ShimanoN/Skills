# EPJ File Structure Templates

Boilerplate for the outer XML wrapper and declaration sections (`Variables`, `Lists`, `KeyValueLists`).

---

## EPJ_HEADER

Opens the file down to the start of `<ExiaBlocks>`.  
All block content is appended after this.

```python
EPJ_HEADER = (
    '<?xml version="1.0"?>\r\n'
    '<ExiaData xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
    ' xmlns:xsd="http://www.w3.org/2001/XMLSchema">\r\n'
    '  <ToolWidth>500</ToolWidth>\r\n'
    '  <OutputHeight>160</OutputHeight>\r\n'
    '  <ProgramAreaScale>1</ProgramAreaScale>\r\n'
    '  <ToolScale>1</ToolScale>\r\n'
    '  <BlockStorageScale>1</BlockStorageScale>\r\n'
    '  <PinFunctionNos />\r\n'
    '  <Functions>\r\n'
    '    <ExiaFunction>\r\n'
    '      <No>0</No>\r\n'
    '      <ExiaBlocks>\r\n'
)
```

---

## EPJ_FOOTER

Closes `<ExiaBlocks>` and appends all declaration sections.  
Replace the `Variables` / `Lists` / `KeyValueLists` blocks as needed — use the snippets below.

```python
EPJ_FOOTER = (
    '      </ExiaBlocks>\r\n'
    '      <IsCloseOutline>false</IsCloseOutline>\r\n'
    '      <IsPin>false</IsPin>\r\n'
    '    </ExiaFunction>\r\n'
    '  </Functions>\r\n'
    + VARIABLES          # see snippets below
    + '  <Constants />\r\n'
    + LISTS              # see snippets below
    + KVL               # see snippets below
    +
    '  <Tables />\r\n'
    '  <Timers />\r\n'
    '  <StorageDatas>\r\n'
    '    <StorageData>\r\n'
    '      <Blocks />\r\n'
    '      <Name>Sheet1</Name>\r\n'
    '    </StorageData>\r\n'
    '  </StorageDatas>\r\n'
    '  <StorageBlocks />\r\n'
    '  <IsStartupExecute>false</IsStartupExecute>\r\n'
    '  <MainArguments />\r\n'
    '  <WatchList />\r\n'
    '  <HttpTimeout>5000</HttpTimeout>\r\n'
    '  <IsShare>false</IsShare>\r\n'
    '  <PortNo>9000</PortNo>\r\n'
    '</ExiaData>\r\n'
)
```

---

## Variables declaration snippets

### No variables
```python
VARIABLES = '  <Variables />\r\n'
```

### One variable
```python
VARIABLES = (
    '  <Variables>\r\n'
    '    <ExiaVariable>\r\n'
    '      <No>0</No>\r\n'
    '      <Name>state</Name>\r\n'
    '      <Comment>state value</Comment>\r\n'
    '      <AccessLevel>0</AccessLevel>\r\n'
    '    </ExiaVariable>\r\n'
    '  </Variables>\r\n'
)
```

### Multiple variables — repeat `<ExiaVariable>` blocks, incrementing `<No>`
```python
VARIABLES = (
    '  <Variables>\r\n'
    '    <ExiaVariable><No>0</No><Name>state</Name>'
        '<Comment>state value</Comment><AccessLevel>0</AccessLevel></ExiaVariable>\r\n'
    '    <ExiaVariable><No>1</No><Name>result</Name>'
        '<Comment>True=OK / False=NG</Comment><AccessLevel>0</AccessLevel></ExiaVariable>\r\n'
    '  </Variables>\r\n'
)
```

---

## Lists declaration snippets

### No lists
```python
LISTS = '  <Lists />\r\n'
```

### doState (standard APS valve list)
```python
LISTS = (
    '  <Lists>\r\n'
    '    <ExiaList>\r\n'
    '      <No>0</No>\r\n'
    '      <Name>doState</Name>\r\n'
    '      <Comment>[0]=SOV-01(DO-001) / [1]=EV-OUT(DO-002) / [2]=EV-BYP(DO-011)</Comment>\r\n'
    '      <AccessLevel>0</AccessLevel>\r\n'
    '    </ExiaList>\r\n'
    '  </Lists>\r\n'
)
```

---

## KeyValueLists declaration snippets

### No KVLs
```python
KVL = '  <KeyValueLists />\r\n'
```

### One KVL (IO-Link process data)
```python
KVL = (
    '  <KeyValueLists>\r\n'
    '    <ExiaKeyValueList>\r\n'
    '      <No>0</No>\r\n'
    '      <Name>processKVL</Name>\r\n'
    '      <Comment>IO-Link process data</Comment>\r\n'
    '      <AccessLevel>0</AccessLevel>\r\n'
    '    </ExiaKeyValueList>\r\n'
    '  </KeyValueLists>\r\n'
)
```

---

## File write pattern (mandatory)

```python
out_path = r'C:\gemini\APS\プログラム\FB_XXX_test.epj'
xml_str = EPJ_HEADER + content + EPJ_FOOTER

# open with newline='\r\n' then strip \r so Python's universal newline
# translation doesn't double the carriage returns
with open(out_path, 'w', encoding='utf-8', newline='\r\n') as f:
    f.write(xml_str.replace('\r\n', '\n'))

print(f'Written: {out_path}')
print(f'  size (LF-normalized): {len(xml_str.replace(chr(13), ""))} bytes')
```
