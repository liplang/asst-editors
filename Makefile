ROOT := $(CURDIR)
BUILD ?= $(ROOT)/.build
export LIP_EDITOR_BUILD := $(abspath $(BUILD))
export GOCACHE := $(LIP_EDITOR_BUILD)/cache
export GOTMPDIR := $(LIP_EDITOR_BUILD)/tmp
export GOPATH := $(LIP_EDITOR_BUILD)/gopath

.PHONY: all tools generate test clean
all: tools
tools:
	@mkdir -p "$(BUILD)/bin" "$(GOCACHE)" "$(GOTMPDIR)" "$(GOPATH)"
	go build -buildvcs=false -o "$(BUILD)/bin/lipcheck" ./tools/lipcheck
	go build -buildvcs=false -o "$(BUILD)/bin/lipc" lip/cmd/lipc
generate:
	python3 tools/generate.py
test: tools
	python3 tests/check.py
clean:
	rm -rf "$(BUILD)"
	find . -type d \( -name __pycache__ -o -name .pytest_cache -o -name .mypy_cache -o -name .ruff_cache \) -prune -exec rm -rf {} +
	find . -type f \( -name '*.pyc' -o -name '*.pyo' -o -name '*.elc' -o -name '*.vsix' -o -name 'nvim.log' \) -delete
