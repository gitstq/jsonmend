# Contributing to jsonmend

Thanks for taking the time to contribute! 🎉 The following guidelines help keep
the project consistent and easy to maintain. These are guidelines, not hard
rules — use your best judgment.

🌐 Read these docs in another language:
[简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [English](README.en.md)

## Ways to contribute

- 🐛 Report bugs and "JSON that cannot be repaired" via
  [Issues](https://github.com/gitstq/jsonmend/issues);
- 💡 Suggest new features or improvements;
- 📝 Improve documentation or add examples;
- 🔧 Submit pull requests with fixes and new repair capabilities.

## Development setup

jsonmend has **zero runtime dependencies**; only a recent Python is needed.

```bash
git clone https://github.com/gitstq/jsonmend.git
cd jsonmend
pip install -e .
python3 -m unittest discover -s tests
```

## Coding standards

- Keep the core **dependency-free** (Python standard library only);
- prefer clear, well-commented, deterministic code;
- add unit tests for every new rule or fix;
- make sure the full suite passes before opening a PR.

## Commit messages

Follow the [Angular / Conventional Commits](https://www.conventionalcommits.org/)
style:

- `feat: add ...`
- `fix: repair ...`
- `docs: document ...`
- `refactor: refactor ...`
- `test: add tests ...`

## Pull requests

1. Fork the repository and create a branch (`feat/...` or `fix/...`);
2. describe the motivation and usage in the PR description;
3. link any related issues;
4. ensure tests pass and (where relevant) add fixtures under `tests/fixtures/`.

## Reporting an unrepairable sample

Please include:

- a **minimal reproducible sample**;
- the expected output;
- the Python/OS version and the jsonmend version (`jsonmend --version`).

Do not include real secrets or personal data in public issues.

## Code of conduct

Be respectful and constructive. We want a welcoming space for contributors of
all backgrounds.

## License

By contributing, you agree that your contributions are licensed under the
project's [MIT License](LICENSE).
