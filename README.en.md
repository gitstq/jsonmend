# 🩹 jsonmend

🌐 **Language**: [简体中文](README.zh-CN.md) ｜ [繁體中文](README.zh-TW.md) ｜ English

<p align="center">
  <b>Mend the "dirty JSON" returned by LLMs/agents so structured output just works.</b><br/>
  Extract → Clean → Complete truncation → Stream partial JSON → Validate against a schema.
</p>

<p align="center">
  <img alt="python" src="https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white" />
  <img alt="deps" src="https://img.shields.io/badge/dependencies-zero-2dd4bf" />
  <img alt="license" src="https://img.shields.io/badge/License-MIT-green" />
  <img alt="tests" src="https://img.shields.io/badge/tests-82%20passing-success" />
</p>

---

## 🎉 Introduction

**jsonmend** is a local-first, zero-dependency, deterministic "broken JSON repair engine" built for a problem every LLM / AI-agent developer keeps hitting:

> You ask the model to "respond in JSON", but it comes back wrapped in Markdown fences, single quotes, trailing commas, `// comments`, `True / False / None`, bare keys, or cut off mid-stream. Calling `json.loads` immediately throws.

jsonmend reliably turns that input into **strict, standard JSON that any language can parse**, and it **tells you exactly what it changed and how confident it is** — no regex brace-guessing, no network calls, no data leaving your machine.

- 🧭 **Position**: the "last mile" safety layer for structured LLM/agent output.
- 💊 **Value**: turns "parse failed, pipeline broken" into "silently repaired, stable by default".
- 🪞 **Differentiators**:
  - a **character-level state machine** that correctly handles braces, quotes and comments that live *inside* strings;
  - **truncation-aware, incremental streaming repair** for tokens arriving over SSE / streaming agents;
  - **explainable diagnostics + confidence** for a white-box repair process;
  - **JSON Schema integration** — type coercion, defaults, enum repair — also used to pick the best of several candidates;
  - **zero dependencies (stdlib only)** with a Python library, a cross-platform CLI and a single-file browser playground.
- 💡 **Inspiration**: observing the widespread need for reliable structured output amid the current wave of agent tooling. All code is independently written; only the problem itself is referenced.

---

## ✨ Features

- 🔍 **Extraction**: locate JSON inside ` ```json ... ``` ` fences, prose wrappers, or **multiple blobs** in one text; a `}` or a ```` ``` ```` inside a string cannot fool it.
- 🧹 **Context-aware cleaning**:
  - single / smart quotes (‘ ’ “ ”) → standard double quotes;
  - remove `// line` and `/* block */ comments` (comment-like text inside strings is preserved);
  - remove **trailing commas** in objects and arrays;
  - quote **bare keys** such as `name: "x"`;
  - Python/JS literals `True / False / None / undefined` → `true / false / null`;
  - non-standard constants `NaN / Infinity` → `null`;
  - insert **missing commas / colons** and escape raw control characters;
  - normalize hexadecimal / octal and other non-standard numbers.
- 🩹 **Truncation completion**: close unterminated strings, arrays and objects, and safely drop an incomplete tail (`{"a":1,"b":` → `{"a":1}`).
- 🌊 **Streaming**: `StreamMender` accepts chunks, returns the best value derivable so far, and signals completion when the structure closes naturally.
- 📐 **Schema validation/coercion**: supports `type / properties / required / items / enum / const / default / length / range / pattern`, and scores candidates to choose the best.
- 🧾 **Explainable diagnostics**: every fix carries a stable `code`, location, severity (minor/major) and `before → after`.
- 📦 **Zero dependencies & privacy-first**: Python stdlib only, fully offline, no telemetry; plus a **single-file browser playground**.

---

## 🚀 Quick Start

### 🧰 Requirements

- Python **3.8 or newer** (3.10+ recommended);
- no third-party dependencies; the CLI works on Windows, macOS and Linux.

### 📥 Install

Install directly from GitHub (this also installs the `jsonmend` command):

```bash
pip install git+https://github.com/gitstq/jsonmend.git
```

Or clone and install in editable mode:

```bash
git clone https://github.com/gitstq/jsonmend.git
cd jsonmend
pip install -e .
```

**Prefer not to install?** Run straight from source (the tests are also dependency-free):

```bash
export PYTHONPATH=src
python3 -m jsonmend --help
python3 -m unittest discover -s tests
```

### ▶️ Try it in one line

```bash
echo 'Sure, here: ```json {"a": 1, "b": 2,} ```' | jsonmend
```

Output:

```json
{
  "a": 1,
  "b": 2
}
```

### 🐍 Use it in code

```python
from jsonmend import mend

llm_output = '```json\n{"name": "Ada", active: True, "tags": ["a","b",],}\n```'

value = mend(llm_output)
# {'name': 'Ada', 'active': True, 'tags': ['a', 'b']}

# When you need diagnostics:
report = mend(llm_output, return_report=True)
print(report.confidence)     # 0.xx
print(report.change_codes)   # ['removed_fence', 'literal_normalized', ...]
```

---

## 📖 Usage Guide

### 1️⃣ Core API

| API | Description |
| --- | --- |
| `mend(text, **opts)` | Repair and return a Python object (`return_report=True` for the full report) |
| `loads(text, **opts)` | Tolerant alias for `mend` |
| `loads_many(text)` | Parse **every** JSON document in the text |
| `extract_json(text)` | Return raw candidate fragments (fences stripped) |
| `mend_file(path, **opts)` | Read a file and repair it |
| `StreamMender(schema=...)` | Incremental streaming repairer (`feed` / `finish` / `complete`) |

Common options for `mend`:

- `schema=dict`: validate/coerce against a JSON Schema;
- `coerce=True`: perform schema coercion (`False` to validate only);
- `strict=True`: do not repair, parse strictly (for CI);
- `many=True`: parse every document;
- `return_report=True`: return a `MendResult` with `value / ok / confidence / changes / schema_issues`.

### 2️⃣ Truncated / streaming JSON

```python
from jsonmend import StreamMender

mender = StreamMender()
for chunk in ["{'a':", " 1, 'b':", " [1,2]}"]:
    value = mender.feed(chunk)   # current best value, never raises
print(mender.complete)           # True
print(mender.finish().value)     # {'a': 1, 'b': [1, 2]}
```

You can also repair a truncated fragment directly:

```python
from jsonmend import mend

mend('{"events": [1, 2,')   # {'events': [1, 2]}
mend('{"a": "unclosed')      # {'a': 'unclosed'}
```

### 3️⃣ With a JSON Schema

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

# bare keys + numeric strings + a wrong-case enum are all repaired and coerced
mend('{name: "Grace", age: "36", role: ADMIN}', schema=schema)
# {'name': 'Grace', 'age': 36, 'role': 'admin'}
```

### 4️⃣ CLI

```bash
jsonmend dirty.txt > clean.json          # repair a file
echo "{'a': 1}" | jsonmend               # stdin
jsonmend -c '{"a":1,}' --compact         # inline string, compact output
jsonmend payload.json --check            # CI gate: exit 1 if repair is needed
jsonmend payload.json --diagnostics      # print a repair report to stderr
jsonmend -c '{"a":1} x {"b":2}' --many   # parse multiple documents
curl -N <stream> | jsonmend --stream      # streaming repair
```

### 5️⃣ Browser playground

No server or build step: open [`web/index.html`](web/index.html) in any browser. Paste the model's dirty text on the left; the repaired result and item-by-item diagnostics appear on the right. Everything runs locally.

> 📸 A live example is loaded on startup; click `sample: truncated` to see truncation repair.

---

## 💡 Design & Roadmap

### 🧠 Why not regex replacement?

Regex deletion of trailing commas and brace-patching cannot tell a structural `}` from one **inside a string**, which is how content gets corrupted. jsonmend uses a deterministic two-stage design:

1. **Forgiving tokenizer**: a character-level scan that understands strings, escapes, comments, literals and numbers while tokenizing;
2. **Rebuilder**: reconstruct canonical JSON using an object/array grammar stack, inserting commas/colons and removing trailing commas in the right places; on truncation it rolls back to the *last complete element* before closing brackets.

The stdlib `json.loads` then verifies the result as a gold standard, with a hand-written recursive-descent parser as a fallback.

### 🧭 Principles

- 🧱 **Deterministic**: the same input always yields the same output — ideal for CI/regression;
- 🔒 **Privacy-first, fully offline**: nothing is sent anywhere by default;
- 🪶 **Zero dependencies**: the stdlib is enough — no supply-chain risk or environment traps;
- 🩻 **White-box & explainable**: repair is not magic; every step is recorded with confidence.

### 🗺️ Roadmap

- [ ] More JSON Schema keywords (`oneOf / anyOf / allOf / format`);
- [ ] Incremental complexity optimization for streaming (the current re-parse of a single message is fine for typical use);
- [ ] Bindings/examples for more languages;
- [ ] Pluggable repair strategies and custom rules;
- [ ] A richer regression corpus of real-world dirty samples.

Please share any "JSON you cannot fix" in [Issues](https://github.com/gitstq/jsonmend/issues).

---

## 📦 Packaging & Deployment

jsonmend is a **library / CLI**, so no executable Release is required. Choose what you need:

- **As a library**: `pip install git+https://github.com/gitstq/jsonmend.git`, then `from jsonmend import mend`;
- **As a CLI**: run `jsonmend` after install, cross-platform (any Python environment);
- **Build distributions** (optional):

  ```bash
  pip install build
  python3 -m build      # sdist / wheel land in dist/
  ```

- **Offline web**: copy `web/index.html` to any machine and open it in a browser;
- **Compatibility**: Python 3.8–3.13, OS-independent, no network or native components.

---

## 🤝 Contributing

Thanks for your interest in jsonmend! 🎉

1. Fork the repo and create a branch: `git checkout -b feat/my-feature`;
2. Follow the **Angular commit conventions**:
   - `feat: add a feature`
   - `fix: fix a bug`
   - `docs: documentation`
   - `refactor: refactor code`
   - `test: tests`
3. Add unit tests for features/fixes and make sure:

   ```bash
   python3 -m unittest discover -s tests
   ```

   passes;
4. Open a Pull Request describing the motivation and usage.

### 🐛 Issues

- When reporting "unrepairable JSON", include a **minimal reproducible sample** and the expected result;
- please avoid disclosing sensitive information in public issues.

---

## 📄 License

Released under the **[MIT License](LICENSE)** — free to use, modify and distribute, with the original copyright notice retained.

<p align="center">🩹 If jsonmend saved you debugging time, a Star ⭐ is appreciated.</p>
