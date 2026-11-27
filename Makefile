PYTHON ?= python3
VENV := .venv
VENV_PYTHON := $(VENV)/bin/python
DEPENDENCY_STAMP := $(VENV)/.requirements-installed

.PHONY: help setup install run practice test test-domain test-generator test-gemini test-cli

help:
	@echo "Development commands:"
	@echo "  make setup           Create .venv and install dependencies"
	@echo "  make run             Generate a quiz with Gemini"
	@echo "  make practice        Start the offline sample quiz"
	@echo "  make test            Run all tests"
	@echo "  make test-domain     Run Question and Quiz model tests"
	@echo "  make test-generator  Run QuizGenerator tests"
	@echo "  make test-gemini     Run mocked Gemini provider tests"
	@echo "  make test-cli        Run terminal, file, export, and startup tests"

setup: $(DEPENDENCY_STAMP)

install: $(DEPENDENCY_STAMP)

$(VENV_PYTHON):
	$(PYTHON) -m venv $(VENV)

$(DEPENDENCY_STAMP): requirements.txt | $(VENV_PYTHON)
	$(VENV_PYTHON) -m pip install -r requirements.txt
	@touch $(DEPENDENCY_STAMP)

run: $(DEPENDENCY_STAMP)
	$(VENV_PYTHON) -m ai_quiz_generator.main

practice: $(DEPENDENCY_STAMP)
	$(VENV_PYTHON) -m ai_quiz_generator.main --practice

test: $(DEPENDENCY_STAMP)
	$(VENV_PYTHON) -m pytest -q

test-domain: $(DEPENDENCY_STAMP)
	$(VENV_PYTHON) -m pytest tests/test_domain_models.py -q

test-generator: $(DEPENDENCY_STAMP)
	$(VENV_PYTHON) -m pytest tests/test_quiz_generator.py -q

test-gemini: $(DEPENDENCY_STAMP)
	$(VENV_PYTHON) -m pytest tests/test_gemini_provider.py -q

test-cli: $(DEPENDENCY_STAMP)
	$(VENV_PYTHON) -m pytest tests/test_terminal_ui.py tests/test_input_reader.py tests/test_quiz_exporter.py tests/test_main.py -q
