.PHONY: up install clean

up:
	docker-compose up --build

down:
	docker-compose down

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
	@echo "Resetting database data..."
	docker-compose exec database psql -U db_user -d messaging -c "TRUNCATE TABLE messages RESTART IDENTITY CASCADE;"
	@echo "Database data cleared"

reset-rabbitmq:
	@echo "Resetting RabbitMQ queues..."
	docker-compose exec rabbitmq rabbitmqctl purge_queue message_processing_queue
	@echo "RabbitMQ queues purged"