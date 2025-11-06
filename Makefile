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
