SHELL := /bin/bash

.PHONY: proto test test-cov

proto:
	bash scripts/compile_protos.sh

test:
	python -m pytest tests/ -v

test-cov:
	python -m pytest tests/ --cov=app --cov-report=term-missing
