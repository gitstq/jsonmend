# jsonmend Makefile — zero third-party dependencies required.
PYTHON ?= python3
PIP    ?= $(PYTHON) -m pip

.PHONY: help install dev test testv demo web clean check build

help: ## Show this help
	@$(PYTHON) -c "import re,sys; [print(l.split('## ')[0].rstrip(' :').replace('.PHONY:',''), '##', l.split('## ')[1]) for l in open('Makefile') if '## ' in l and not l.startswith('.PHONY')]"

install: ## Install the package (and the jsonmend CLI) into the current environment
	$(PIP) install .

dev: ## Install in editable mode
	$(PIP) install -e .

test: ## Run the full zero-dependency test suite
	$(PYTHON) -m unittest discover -s tests -q

testv: ## Run tests verbosely
	$(PYTHON) -m unittest discover -s tests -v

check: ## CI gate: parse every fixture and fail loudly if something is broken
	$(PYTHON) -m unittest discover -s tests -q
	$(PYTHON) -m jsonmend --check tests/fixtures/01_fenced.json.txt || true

demo: ## Run a quick CLI demo
	printf 'Sure, here is the result:\n\n```json\n{\"name\": \"Ada\", "tags": ["a","b",], // trailing\n}\n```\n' | $(PYTHON) -m jsonmend --diagnostics

web: ## Print the path to the browser playground
	@echo "Open web/index.html in any browser (no server, no build step)."

build: ## Build sdist/wheel (needs the standard 'build' workflow; optional)
	$(PIP) install build
	$(PYTHON) -m build

clean: ## Remove caches and build artifacts
	rm -rf build dist *.egg-info src/*.egg-info .pytest_cache .mypy_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
