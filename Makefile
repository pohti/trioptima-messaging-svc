.PHONY: up down install clean

VENV = .venv
PYTHON = $(VENV)/bin/python3
PIP = $(VENV)/bin/pip
DATABASE_URL = postgresql://db_user:db_password@database:5432/messaging

# Create virtual environment and install dependencies
install:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

up:
	docker-compose up --build

down:
	docker-compose down

test: reset-db
	$(PYTHON) -m pytest tests/ -v
	@$(MAKE) reset-db

# Clean up everything
clean:
	rm -rf .venv
	rm -rf __pycache__
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf messages.db
	rm -rf test.db

# reset commands
reset-data: reset-db reset-rabbitmq
	@echo "All data reset complete"

reset-db:
	@echo "Resetting database..."
	docker-compose exec database psql -U db_user -d messaging -c "TRUNCATE TABLE messages RESTART IDENTITY CASCADE;"
	@echo "Database cleared"

reset-rabbitmq:
	@echo "Resetting RabbitMQ queues..."
	docker-compose exec rabbitmq rabbitmqctl purge_queue message_processing_queue
	@echo "RabbitMQ queues purged"