.PHONY: test run contrato docker-build run-docker reproduce dashboard

IMAGEM ?= lab03-dora
CONFIG ?= config.yaml

test:
	pytest --cov=metricas --cov=coleta --cov-report=term-missing --cov-fail-under=80

run:
	python -m pipeline --config $(CONFIG)

contrato:
	python -m metricas.dicionario
	git diff --exit-code docs/dicionario_dados.md

docker-build:
	docker build -t $(IMAGEM) .

run-docker: docker-build
	docker run --rm $(if $(wildcard .env),--env-file .env) -e GITHUB_TOKEN -v "$(CURDIR)/data:/app/data" $(IMAGEM) --config $(CONFIG)

reproduce:
	python -m analise

dashboard:
	python -m analise.painel
