.PHONY: help install dev lint fmt test run docker

help:
	@echo "Targets: install dev lint fmt test run docker"

install:
	pip install -r requirements.txt

dev:
	pip install -r requirements.txt -r requirements-dev.txt

lint:
	ruff check .

fmt:
	black .

test:
	pytest -q

run:
	./start.sh

docker:
	docker build -t mordzix-ai:latest .
