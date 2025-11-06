.PHONY: up install python test clean

VENV = .venv
PYTHON = $(VENV)/bin/python3
PIP = $(VENV)/bin/pip

up:
	docker-compose up --build --scale messaging-svc=3

down:
	docker-compose down

# Create virtual environment and install dependencies
install:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

freeze: 
	$(PIP) freeze > requirements.txt

# Test environment
test-setup:
	docker-compose -f docker-compose.test.yml up -d --build
	@echo "Waiting for test services to be ready..."
	@sleep 15

test-cleanup:
	docker-compose -f docker-compose.test.yml down -v

test-integration: test-setup
	@echo "Running integration tests..."
	TEST_BASE_URL=http://localhost:8001 pytest tests/test_main.py -v --tb=short
	$(MAKE) test-cleanup

# Clean up everything
clean:
	rm -rf $(VENV)
	rm -rf __pycache__
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf messages.db
	rm -rf test.db
