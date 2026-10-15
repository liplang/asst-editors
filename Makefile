ROOT := $(abspath ..)
BUILD := $(ROOT)/.build/editors
export GOCACHE := $(ROOT)/.build/cache
export GOTMPDIR := $(ROOT)/.build/tmp
export GOPATH := $(ROOT)/.build/gopath

.PHONY: all tools generate test clean
all: tools
tools:
	@mkdir -p "$(BUILD)/bin" "$(GOCACHE)" "$(GOTMPDIR)" "$(GOPATH)"
	cd "$(ROOT)" && go build -o "$(BUILD)/bin/lipcheck" ./editors/tools/lipcheck
	cd "$(ROOT)" && go build -o "$(BUILD)/bin/lipc" ./cmd/lipc
generate:
	python3 tools/generate.py
test: tools
	python3 tests/check.py
clean:
	rm -rf "$(BUILD)"
	find . -type d \( -name __pycache__ -o -name .pytest_cache -o -name .mypy_cache -o -name .ruff_cache \) -prune -exec rm -rf {} +
	find . -type f \( -name '*.pyc' -o -name '*.pyo' -o -name '*.elc' -o -name '*.vsix' -o -name 'nvim.log' \) -delete
