# 🩹 jsonmend

🌐 **語言**：[简体中文](README.zh-CN.md) ｜ 繁體中文 ｜ [English](README.en.md)

<p align="center">
  <b>修補大模型 / Agent 回傳的「髒 JSON」，讓結構化輸出真正開箱即用。</b><br/>
  擷取 → 清理 → 截斷補全 → 串流增量修復 → Schema 驗證，完整閉環。
</p>

<p align="center">
  <img alt="python" src="https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white" />
  <img alt="deps" src="https://img.shields.io/badge/dependencies-zero-2dd4bf" />
  <img alt="license" src="https://img.shields.io/badge/License-MIT-green" />
  <img alt="tests" src="https://img.shields.io/badge/tests-82%20passing-success" />
</p>

---

## 🎉 專案介紹

**jsonmend** 是一個本地優先、零依賴、具決定性的「破損 JSON 修復引擎」，專門解決每位 LLM / AI Agent 開發者都會一再遇到的痛點：

> 你請模型「以 JSON 格式回覆」，它卻回你一段夾雜 Markdown 程式碼包覆、單引號、尾隨逗號、`// 註解`、`True / False / None`、裸漏鍵名，甚至在串流時被截斷的文字。直接呼叫 `json.loads` 馬上報錯。

jsonmend 會穩穩地把這樣的輸入修復成**標準、嚴格、任何語言都能解析的 JSON**，而且**明確告訴你它改了什麼、信心程度為何**——過程不靠正則硬湊括號、不需連網、不會送出任何資料。

- 🧭 **定位**：LLM / Agent 結構化輸出的「最後一哩」保障層。
- 💊 **核心價值**：把「解析失敗、流程中斷」變成「靜默修復、穩定執行」。
- 🪞 **自研差異化亮點**：
  - **字元級狀態機掃描**，正確辨識字串內部的括號、引號與註解，絕不誤傷；
  - **截斷感知＋串流增量修復**，token 邊到邊解析（適配 SSE / 串流 Agent）；
  - **可解釋診斷報告＋信心程度**，修復過程白盒可見；
  - **JSON Schema 聯動**：型別強制、預設值補全、列舉修復，並從多個候選中擇優；
  - **零依賴、純標準函式庫**，同時提供 Python 函式庫、跨平台 CLI 與單檔瀏覽器 Playground。
- 💡 **靈感來源**：來自觀察當前 Agent 工程化浪潮（Agent 管理、記憶、工具呼叫等）中「結構化輸出可靠性」的普遍痛點，全部程式碼皆為獨立自研，僅參考問題本身。

---

## ✨ 核心特性

- 🔍 **智慧擷取（Extract）**：從 ` ```json ... ``` ` 程式碼包覆、自然語言前綴後綴，甚至同一段文字中的**多個 JSON** 裡定位目標；字串裡出現的 `}`、```` ``` ```` 也不會造成干擾。
- 🧹 **上下文感知清理（Clean）**：
  - 單引號 / 智慧引號（‘ ’ “ ”）→ 標準雙引號；
  - 移除 `// 單行註解` 與 `/* 區塊註解 */`（字串內的註解字樣會被保留）；
  - 移除物件 / 陣列的**尾隨逗號**；
  - **裸漏鍵** `name: "x"` 自動加上引號；
  - Python / JS 字面量 `True / False / None / undefined` → `true / false / null`；
  - `NaN / Infinity` 等非標準常數 → `null`；
  - 自動補上**遺漏的逗號 / 冒號**，跳脫字串內的原始控制字元；
  - 支援十六進位 / 八進位等非標準數字正規化。
- 🩹 **截斷補全（Complete）**：自動閉合未終止的字串、陣列與物件，並安全丟棄不完整的尾部片段（如 `{"a":1,"b":` → `{"a":1}`）。
- 🌊 **串流增量（Streaming）**：`StreamMender` 逐塊接收 token，隨時回傳目前可確定的值，結構自然閉合時給出完成標記。
- 📐 **Schema 驗證與強制（Coerce）**：支援 `type / properties / required / items / enum / const / default / 長度 / 範圍 / pattern`，並對多個候選按匹配度打分擇優。
- 🧾 **可解釋診斷**：每處修復都帶有穩定的 `code`、位置、嚴重程度（minor / major）與 `before → after`。
- 📦 **零依賴＆隱私優先**：僅使用 Python 標準函式庫，完全離線、無遙測；另附**單檔瀏覽器 Playground**，開啟即用。

---

## 🚀 快速開始

### 🧰 環境需求

- Python **3.8 或更新版本**（建議 3.10+）；
- 無任何第三方依賴；CLI 於 Windows / macOS / Linux 皆可使用。

### 📥 安裝

直接從 GitHub 安裝（同時安裝好 `jsonmend` 指令）：

```bash
pip install git+https://github.com/gitstq/jsonmend.git
```

或複製原始碼後以可編輯模式安裝：

```bash
git clone https://github.com/gitstq/jsonmend.git
cd jsonmend
pip install -e .
```

**不想安裝？** 直接用原始碼執行（測試同樣零依賴）：

```bash
export PYTHONPATH=src
python3 -m jsonmend --help
python3 -m unittest discover -s tests
```

### ▶️ 一行指令體驗

```bash
echo 'Sure, here: ```json {"a": 1, "b": 2,} ```' | jsonmend
```

輸出：

```json
{
  "a": 1,
  "b": 2
}
```

### 🐍 在程式碼中使用

```python
from jsonmend import mend

llm_output = '```json\n{"name": "Ada", active: True, "tags": ["a","b",],}\n```'

value = mend(llm_output)
# {'name': 'Ada', 'active': True, 'tags': ['a', 'b']}

# 需要診斷資訊時：
report = mend(llm_output, return_report=True)
print(report.confidence)      # 0.xx
print(report.change_codes)    # ['removed_fence', 'literal_normalized', ...]
```

---

## 📖 詳細使用指南

### 1️⃣ 核心 API

| API | 說明 |
| --- | --- |
| `mend(text, **opts)` | 修復並回傳 Python 物件（`return_report=True` 回傳完整報告） |
| `loads(text, **opts)` | `mend` 的容錯別名 |
| `loads_many(text)` | 解析文字中**所有** JSON，回傳列表 |
| `extract_json(text)` | 回傳原始候選片段（包覆已移除） |
| `mend_file(path, **opts)` | 讀取檔案並修復 |
| `StreamMender(schema=...)` | 串流增量修復器（`feed` / `finish` / `complete`） |

`mend` 常用參數：

- `schema=dict`：傳入 JSON Schema，進行驗證與型別強制；
- `coerce=True`：是否執行 Schema 強制（設為 `False` 僅驗證）；
- `strict=True`：不修復，僅嚴格解析（用於 CI）；
- `many=True`：解析全部 JSON；
- `return_report=True`：回傳含 `value / ok / confidence / changes / schema_issues` 的 `MendResult`。

### 2️⃣ 修復截斷 / 串流 JSON

```python
from jsonmend import StreamMender

mender = StreamMender()
for chunk in ["{'a':", " 1, 'b':", " [1,2]}"]:
    value = mender.feed(chunk)   # 隨時取得目前最佳值，絕不報錯
print(mender.complete)           # True
print(mender.finish().value)     # {'a': 1, 'b': [1, 2]}
```

也可直接修復一段被截斷的文字：

```python
from jsonmend import mend

mend('{"events": [1, 2,')   # {'events': [1, 2]}
mend('{"a": "未閉合')        # {'a': '未閉合'}
```

### 3️⃣ 結合 JSON Schema

```python
schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "age":  {"type": "integer", "default": 0},
        "role": {"enum": ["admin", "user"]},
    },
    "required": ["name", "age", "role"],
}

# 裸漏鍵＋數字型字串＋大小寫錯誤的列舉，都會被修復並強制
mend('{name: "Grace", age: "36", role: ADMIN}', schema=schema)
# {'name': 'Grace', 'age': 36, 'role': 'admin'}
```

### 4️⃣ CLI 用法

```bash
jsonmend dirty.txt > clean.json          # 修復檔案
echo "{'a': 1}" | jsonmend               # 標準輸入
jsonmend -c '{"a":1,}' --compact         # 直接傳字串，緊湊輸出
jsonmend payload.json --check            # CI 門檻：需要修復則退出碼 1
jsonmend payload.json --diagnostics      # 於 stderr 列印修復報告
jsonmend -c '{"a":1} x {"b":2}' --many   # 解析多個 JSON
curl -N <串流端點> | jsonmend --stream     # 串流修復
```

### 5️⃣ 瀏覽器 Playground

無需伺服器、無需建置，直接用瀏覽器開啟 [`web/index.html`](web/index.html)：左側貼上模型回傳的髒文字，右側即時顯示修復結果與逐條診斷，所有處理皆於本機完成。

> 📸 展示畫面：見 `web/index.html`（首屏內建範例，可點擊 `sample: truncated` 查看截斷修復）。

---

## 💡 設計思路與迭代規劃

### 🧠 為什麼不用「正則取代」？

以正則刪尾隨逗號、補括號看似簡單，卻無法區分**字串內部**的 `}`、`//`、引號，極易把內容改壞。jsonmend 採用兩段式決定性設計：

1. **容錯 Tokenizer**：字元級掃描，在切詞階段就理解字串、跳脫、註解、字面量與數字；
2. **語法重建器（Rebuilder）**：依據物件 / 陣列的語法堆疊重建規範 JSON，在正確位置補逗號 / 冒號、移除尾隨逗號；遇到截斷時，先回退到「最後一個完整元素」再閉合括號。

最後以標準函式庫 `json.loads` 作為金標準驗證，並以自研遞迴下降剖析器作為兜底。

### 🧭 設計原則

- 🧱 **決定性**：同樣輸入永遠得到同樣輸出，便於 CI / 回歸使用；
- 🔒 **隱私優先、完全離線**：預設不對外傳送任何資料；
- 🪶 **零依賴**：標準函式庫即可執行，避免供應鏈風險與環境陷阱；
- 🩻 **白盒可解釋**：修復不是魔術，每一步都有記錄與信心程度。

### 🗺️ 迭代計畫

- [ ] 支援更多 JSON Schema 關鍵字（`oneOf / anyOf / allOf / format`）；
- [ ] 串流剖析的增量複雜度最佳化（目前對單一訊息重複全量解析，已足夠一般使用）；
- [ ] 更多語言的綁定 / 範例；
- [ ] 可插拔的修復策略與自訂規則；
- [ ] 更豐富的真實世界髒樣本回歸庫。

歡迎至 [Issues](https://github.com/gitstq/jsonmend/issues) 提出你遇到「修不動的 JSON」。

---

## 📦 打包與部署指南

jsonmend 屬於**工具函式庫 / CLI 元件**，無需 Release 可執行檔，依需求選擇：

- **作為函式庫整合**：`pip install git+https://github.com/gitstq/jsonmend.git`，接著 `from jsonmend import mend`；
- **作為 CLI 使用**：安裝後直接執行 `jsonmend`，跨平台（Python 環境）；
- **建置分發包**（選用）：

  ```bash
  pip install build
  python3 -m build      # sdist / wheel 產出於 dist/
  ```

- **離線網頁版**：將 `web/index.html` 複製到任何機器，以瀏覽器開啟即可；
- **相容環境**：Python 3.8–3.13，與作業系統無關；不依賴網路或任何原生元件。

---

## 🤝 貢獻指南

感謝你對 jsonmend 的興趣！🎉

1. Fork 本專案並建立分支：`git checkout -b feat/my-feature`；
2. 請遵循 **Angular 提交規範**：
   - `feat: 新增功能`
   - `fix: 修復問題`
   - `docs: 文件更新`
   - `refactor: 程式重構`
   - `test: 測試相關`
3. 為新功能 / 修復補充對應的單元測試，並確保：

   ```bash
   python3 -m unittest discover -s tests
   ```

   全數通過；
4. 提交合併請求（Pull Request），並於描述說明動機與用法。

### 🐛 回報 Issue

- 提交「無法修復的 JSON」時，請附上**最小可重現樣本**與期望結果；
- 安全議題請避免於公開 Issue 揭露敏感資訊。

---

## 📄 開源授權

本專案依 **[MIT License](LICENSE)** 開源，可自由使用、修改與分發，請保留原始版權聲明。

<p align="center">🩹 如果 jsonmend 幫你省下了除錯時間，歡迎給個 Star ⭐</p>
