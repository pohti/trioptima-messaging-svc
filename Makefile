.PHONY: up install python test clean

VENV = .venv
PYTHON = $(VENV)/bin/python3
PIP = $(VENV)/bin/pip

# Default goal (optional: make running `make` alone create venv)
.DEFAULT_GOAL := install

up:
	docker-compose up --build

# Create virtual environment and install dependencies
$(VENV):
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

install: $(VENV)

freeze: $(VENV)
	$(PIP) freeze > requirements.txt

# Run FastAPI server (depends on venv existing)
python: $(VENV)
	$(PYTHON) -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# Run tests (depends on venv existing)
test: $(VENV)
	$(PYTHON) -m pytest tests/ -v --cov=src --cov-report=html --cov-report=term-missing

# Clean up everything
clean:
	rm -rf $(VENV)
	rm -rf __pycache__
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf messages.db
	rm -rf test.db
