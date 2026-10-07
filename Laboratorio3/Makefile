.PHONY: test run contrato docker-build run-docker reproduce

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
	docker run --rm -e GITHUB_TOKEN -v "$(CURDIR)/data:/app/data" $(IMAGEM) --config $(CONFIG)

reproduce:
	@echo "make reproduce completo entra na S03: regenera as tabelas e figuras"
	@echo "do artigo a partir dos CSVs de data/processed."
	@echo "Hoje roda a coleta e para por ai."
	$(MAKE) run
