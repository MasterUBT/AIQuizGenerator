PYTHON ?= python3
VENV := .venv
VENV_PYTHON := $(VENV)/bin/python
DEPENDENCY_STAMP := $(VENV)/.requirements-installed

.PHONY: help setup install test test-domain test-generator test-gemini

help:
	@echo "Valmira development commands:"
	@echo "  make setup           Create .venv and install dependencies"
	@echo "  make test            Run all Valmira-owned tests"
	@echo "  make test-domain     Run Question and Quiz model tests"
	@echo "  make test-generator  Run QuizGenerator tests"
	@echo "  make test-gemini     Run mocked Gemini provider tests"

setup: $(DEPENDENCY_STAMP)

install: $(DEPENDENCY_STAMP)

$(VENV_PYTHON):
	$(PYTHON) -m venv $(VENV)

$(DEPENDENCY_STAMP): requirements.txt | $(VENV_PYTHON)
	$(VENV_PYTHON) -m pip install -r requirements.txt
	@touch $(DEPENDENCY_STAMP)

test: $(DEPENDENCY_STAMP)
	$(VENV_PYTHON) -m pytest -q

test-domain: $(DEPENDENCY_STAMP)
	$(VENV_PYTHON) -m pytest tests/test_domain_models.py -q

test-generator: $(DEPENDENCY_STAMP)
	$(VENV_PYTHON) -m pytest tests/test_quiz_generator.py -q

test-gemini: $(DEPENDENCY_STAMP)
	$(VENV_PYTHON) -m pytest tests/test_gemini_provider.py -q
