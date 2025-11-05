.PHONY: up install python test clean

VENV = .venv
PYTHON = $(VENV)/bin/python3
PIP = $(VENV)/bin/pip

up:
	docker-compose up --build

# Create virtual environment and install dependencies
install:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

freeze: 
	$(PIP) freeze > requirements.txt

# runs the fastapi app with uvicorn. Requires .venv
python: 
	$(PYTHON) -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

# runs unit tests with coverage. Requires .venv
test:
	$(PYTHON) -m pytest tests/ -v --cov=src --cov-report=html --cov-report=term-missing

# Clean up everything
clean:
	rm -rf $(VENV)
	rm -rf __pycache__
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf messages.db
	rm -rf test.db
