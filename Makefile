# Makefile for common tasks

.PHONY: help install test lint run dashboard migrate clean

help:
	@echo "Available commands:"
	@echo "  make install    - Install dependencies"
	@echo "  make migrate    - Run database migrations"
	@echo "  make run        - Run portfolio for today"
	@echo "  make dashboard  - Launch dashboard"
	@echo "  make test       - Run tests"
	@echo "  make lint       - Run linters"
	@echo "  make clean      - Clean up generated files"

install:
	pip install -e ".[dev,optimizer]"

migrate:
	python portfolio/db/migrations/migrate.py

run:
	python -m portfolio run --asof $$(date +%Y-%m-%d) --mode paper

dashboard:
	uvicorn app.main:app --reload

test:
	pytest tests/ -v

lint:
	ruff check portfolio/ app/ tests/
	mypy portfolio/ app/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf htmlcov/ .coverage
