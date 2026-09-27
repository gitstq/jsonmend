# 🩹 jsonmend

🌐 **语言 / Language**：简体中文 ｜ [繁體中文](README.zh-TW.md) ｜ [English](README.en.md)

<p align="center">
  <b>修补大模型 / Agent 返回的"脏 JSON"，让结构化输出真正开箱可用。</b><br/>
  提取 → 清洗 → 截断补全 → 流式增量修复 → Schema 校验，全链路闭环。
</p>

<p align="center">
  <img alt="python" src="https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white" />
  <img alt="deps" src="https://img.shields.io/badge/dependencies-zero-2dd4bf" />
  <img alt="license" src="https://img.shields.io/badge/License-MIT-green" />
  <img alt="tests" src="https://img.shields.io/badge/tests-82%20passing-success" />
</p>

---

## 🎉 项目介绍

**jsonmend** 是一个本地优先、零依赖、确定性的"破损 JSON 修复引擎"，专门解决一个所有 LLM / AI Agent 开发者都会反复踩中的痛点：

> 你让模型"以 JSON 格式返回"，它却回你一段夹杂着 Markdown 代码围栏、单引号、尾逗号、`// 注释`、`True / False / None`、裸键名、甚至被流式截断的文本。直接 `json.loads` 当场报错。

jsonmend 会把这样的输入稳稳修复成**标准、严格、可被任何语言解析的 JSON**，并且**告诉你它具体改了什么、置信度是多少**——整个过程不依赖正则硬凑括号，不需要联网，不发送任何数据。

- 🧭 **定位**：LLM / Agent 结构化输出的"最后一公里"保障层。
- 💊 **核心价值**：把"解析失败、流程中断"变成"静默修复、稳定运行"。
- 🪞 **自研差异化亮点**：
  - **字符级状态机扫描**，正确识别字符串内部的括号、引号与注释，绝不误伤；
  - **截断感知 + 流式增量修复**，token 边到边解析（适配 SSE / 流式 Agent）；
  - **可解释诊断报告 + 置信度**，修复过程白盒可见；
  - **JSON Schema 联动**：类型强制、默认值补全、枚举修复，并据此在多个候选中择优；
  - **零依赖纯标准库**，同时提供 Python 库、跨平台 CLI 与单文件浏览器 Playground。
- 💡 **灵感来源**：源于对当下 Agent 工程化浪潮（Agent 管理、记忆、工具调用等）中"结构化输出可靠性"这一普遍痛点的观察，全部代码为独立自研，仅参考问题本身。

---

## ✨ 核心特性

- 🔍 **智能提取（Extract）**：从 ` ```json ... ``` ` 代码围栏、自然语言前后缀、甚至一段文本中的**多个 JSON** 中定位目标；字符串里出现的 `}`、```` ``` ```` 也不会干扰判断。
- 🧹 **上下文清洗（Clean）**：
  - 单引号 / 智能引号（‘ ’ “ ”）→ 标准双引号；
  - 删除 `// 行注释` 与 `/* 块注释 */`（字符串内的注释符号会被保留）；
  - 删除对象 / 数组的**尾逗号**；
  - **裸键** `name: "x"` 自动加引号；
  - Python / JS 字面量 `True / False / None / undefined` → `true / false / null`；
  - `NaN / Infinity` 等非标准常量 → `null`；
  - 自动补全**缺失的逗号 / 冒号**，转义字符串内原始控制字符；
  - 支持十六进制 / 八进制等非标准数字规范化。
- 🩹 **截断补全（Complete）**：自动闭合未终止的字符串、数组与对象，并安全丢弃不完整的尾部片段（如 `{"a":1,"b":` → `{"a":1}`）。
- 🌊 **流式增量（Streaming）**：`StreamMender` 逐块接收 token，随时返回当前可确定的值，结构自然闭合时给出完成标记。
- 📐 **Schema 校验与强制（Coerce）**：支持 `type / properties / required / items / enum / const / default / 长度 / 范围 / pattern`，并对多个候选按匹配度打分择优。
- 🧾 **可解释诊断**：每处修复都带有稳定的 `code`、位置、严重级别（minor / major）与 `before → after`。
- 📦 **零依赖 & 隐私优先**：仅用 Python 标准库，完全离线、无遥测；另附**单文件浏览器 Playground**，打开即用。

---

## 🚀 快速开始

### 🧰 环境要求

- Python **3.8 或更高版本**（推荐 3.10+）；
- 无任何第三方依赖；CLI 在 Windows / macOS / Linux 均可使用。

### 📥 安装

从 GitHub 直接安装（同时装好 `jsonmend` 命令）：

```bash
pip install git+https://github.com/gitstq/jsonmend.git
```

或克隆源码后以可编辑模式安装：

```bash
git clone https://github.com/gitstq/jsonmend.git
cd jsonmend
pip install -e .
```

**不想安装？** 直接用源码运行（测试同样零依赖）：

```bash
export PYTHONPATH=src
python3 -m jsonmend --help
python3 -m unittest discover -s tests
```

### ▶️ 一行命令体验

```bash
echo 'Sure, here: ```json {"a": 1, "b": 2,} ```' | jsonmend
```

输出：

```json
{
  "a": 1,
  "b": 2
}
```

### 🐍 在代码中使用

```python
from jsonmend import mend

llm_output = '```json\n{"name": "Ada", active: True, "tags": ["a","b",],}\n```'

value = mend(llm_output)
# {'name': 'Ada', 'active': True, 'tags': ['a', 'b']}

# 需要诊断信息时：
report = mend(llm_output, return_report=True)
print(report.confidence)        # 0.xx
print(report.change_codes)      # ['removed_fence', 'literal_normalized', ...]
```

---

## 📖 详细使用指南

### 1️⃣ 核心 API

| API | 说明 |
| --- | --- |
| `mend(text, **opts)` | 修复并返回 Python 对象（`return_report=True` 返回完整报告） |
| `loads(text, **opts)` | `mend` 的容错别名 |
| `loads_many(text)` | 解析文本中**所有** JSON，返回列表 |
| `extract_json(text)` | 返回原始候选片段（围栏已剥离） |
| `mend_file(path, **opts)` | 读取文件并修复 |
| `StreamMender(schema=...)` | 流式增量修复器（`feed` / `finish` / `complete`） |

`mend` 的常用参数：

- `schema=dict`：传入 JSON Schema，进行校验与类型强制；
- `coerce=True`：是否执行 Schema 强制（设为 `False` 仅校验）；
- `strict=True`：不修复，仅严格解析（用于 CI）；
- `many=True`：解析全部 JSON；
- `return_report=True`：返回含 `value / ok / confidence / changes / schema_issues` 的 `MendResult`。

### 2️⃣ 修复截断 / 流式 JSON

```python
from jsonmend import StreamMender

mender = StreamMender()
for chunk in ["{'a':", " 1, 'b':", " [1,2]}"]:
    value = mender.feed(chunk)   # 随时拿到当前最佳值，绝不抛错
print(mender.complete)           # True
print(mender.finish().value)     # {'a': 1, 'b': [1, 2]}
```

也可以直接修复一段被截断的文本：

```python
from jsonmend import mend

mend('{"events": [1, 2,')   # {'events': [1, 2]}
mend('{"a": "未闭合')        # {'a': '未闭合'}
```

### 3️⃣ 结合 JSON Schema

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

# 裸键 + 数字型字符串 + 大小写错误的枚举，都会被修复并强制
mend('{name: "Grace", age: "36", role: ADMIN}', schema=schema)
# {'name': 'Grace', 'age': 36, 'role': 'admin'}
```

### 4️⃣ CLI 用法

```bash
jsonmend dirty.txt > clean.json          # 修复文件
echo "{'a': 1}" | jsonmend               # 标准输入
jsonmend -c '{"a":1,}' --compact         # 直接传字符串，紧凑输出
jsonmend payload.json --check            # CI 门禁：需要修复则退出码 1
jsonmend payload.json --diagnostics      # 在 stderr 打印修复报告
jsonmend -c '{"a":1} x {"b":2}' --many   # 解析多个 JSON
curl -N <流式接口> | jsonmend --stream     # 流式修复
```

### 5️⃣ 浏览器 Playground

无需服务器、无需构建，直接用浏览器打开 [`web/index.html`](web/index.html)：左侧粘贴模型返回的脏文本，右侧实时显示修复结果与逐条诊断，所有处理均在本地完成。

> 📸 演示截图：见 `web/index.html`（首屏自带示例，可点击 `sample: truncated` 查看截断修复）。

---

## 💡 设计思路与迭代规划

### 🧠 为什么不用"正则替换"？

用正则去删尾逗号、补括号看似简单，却无法区分**字符串内部**的 `}`、`//`、引号，极易把内容改坏。jsonmend 采用两段式确定性设计：

1. **容错 Tokenizer**：字符级扫描，在切词阶段就理解字符串、转义、注释、字面量与数字；
2. **语法重建器（Rebuilder）**：基于对象 / 数组的语法栈重建规范 JSON，在正确的位置补逗号 / 冒号、去尾逗号；遇到截断时，回退到"最后一个完整元素"再闭合括号。

最后以标准库 `json.loads` 作为金标准验证，并以自研递归下降解析器兜底。

### 🧭 设计原则

- 🧱 **确定性**：同样输入永远得到同样输出，便于在 CI / 回归中使用；
- 🔒 **隐私优先、完全离线**：默认不外发任何数据；
- 🪶 **零依赖**：标准库即可运行，避免供应链风险与环境陷阱；
- 🩻 **白盒可解释**：修复不是魔法，每一步都有记录与置信度。

### 🗺️ 迭代计划

- [ ] 支持更多 JSON Schema 关键字（`oneOf / anyOf / allOf / format`）；
- [ ] 流式解析的增量复杂度优化（当前对单条消息重复全量解析，已足够常规使用）；
- [ ] 更多语言的绑定 / 示例；
- [ ] 可插拔的修复策略与自定义规则；
- [ ] 更丰富的真实世界脏样本回归库。

欢迎在 [Issues](https://github.com/gitstq/jsonmend/issues) 中提出你遇到的"修不好的 JSON"。

---

## 📦 打包与部署指南

jsonmend 属于**工具库 / CLI 组件**，无需 Release 可执行文件，按需选择：

- **作为库集成**：`pip install git+https://github.com/gitstq/jsonmend.git`，随后 `from jsonmend import mend`；
- **作为 CLI 使用**：安装后直接运行 `jsonmend`，跨平台（Python 环境）；
- **构建分发包**（可选）：

  ```bash
  pip install build
  python3 -m build      # 产出 sdist / wheel 于 dist/
  ```

- **离线网页版**：将 `web/index.html` 拷贝到任意机器，浏览器打开即可；
- **兼容环境**：Python 3.8–3.13，操作系统无关；不依赖网络与任何原生组件。

---

## 🤝 贡献指南

感谢你对 jsonmend 的兴趣！🎉

1. Fork 本仓库并新建分支：`git checkout -b feat/my-feature`；
2. 请遵循 **Angular 提交规范**：
   - `feat: 新增功能`
   - `fix: 修复问题`
   - `docs: 文档更新`
   - `refactor: 代码重构`
   - `test: 测试相关`
3. 为新功能 / 修复补充对应的单元测试，并确保：

   ```bash
   python3 -m unittest discover -s tests
   ```

   全部通过；
4. 提交 Pull Request，并在描述中说明动机与用法。

### 🐛 反馈 Issue

- 提交"无法修复的 JSON"时，请附上**最小可复现样本**与期望结果；
- 安全问题请避免在公开 Issue 中披露敏感信息。

---

## 📄 开源协议

本项目基于 **[MIT License](LICENSE)** 开源，可自由使用、修改与分发，请保留原始版权声明。

<p align="center">🩹 如果 jsonmend 帮你省下了调试时间，欢迎点一个 Star ⭐</p>
