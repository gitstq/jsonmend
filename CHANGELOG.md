# Changelog

All notable changes to **jsonmend** are documented here. The format is based
on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-09-27

First stable release.

### Added
- Character-level, state-machine **extractor** that pulls JSON out of Markdown
  fences and free-form text while respecting braces/quotes that live inside
  strings and comments.
- Context-aware **cleaner** that fixes Markdown fences, line/block comments,
  single & smart quotes, trailing commas, bare keys, Python/JS literals
  (`True`/`False`/`None`/`undefined`), missing commas/colons, and raw control
  characters.
- Truncation-aware **completer** that closes unterminated strings, arrays and
  objects and safely drops an incomplete tail.
- A tolerant, hand-written recursive-descent **parser** used as a fallback.
- Incremental **streaming** repairer for partial JSON arriving token-by-token
  (SSE / streaming agents).
- A small, dependency-free **JSON Schema subset** validator/coercer
  (`type`, `properties`, `required`, `items`, `enum`, `const`, `default`,
  bounds, length and `pattern`) that also drives best-candidate selection.
- Explainable **diagnostics**: every fix is reported with a code, location and
  confidence.
- Zero-dependency **CLI** (`jsonmend`) with `--check`, `--schema`,
  `--stream`, `--diagnostics` and compact/indent output.
- Single-file, offline **browser playground** (`web/index.html`).
- Full `unittest` suite with realistic dirty-LLM fixtures.

[1.0.0]: https://github.com/gitstq/jsonmend/releases/tag/v1.0.0
