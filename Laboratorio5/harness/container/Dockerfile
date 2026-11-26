# Imagem descartavel do agente: Claude Code na versao FIXA, JDK 21, Maven e git.
# Nada de tests/acceptance nem reference entra aqui, e a execucao monta apenas o workspace (harness/agente.py).
# NAO TESTADA nesta maquina (daemon do Docker desligado): construa e rode harness/container/verificar-imagem.sh
# antes do piloto.
FROM maven:3.9-eclipse-temurin-21
ARG CLAUDE_CODE_VERSION
RUN test -n "$CLAUDE_CODE_VERSION" || (echo "passe --build-arg CLAUDE_CODE_VERSION=<versao de ambiente.pins>" && exit 1)
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=node:20-bookworm-slim /usr/local/ /usr/local/
RUN npm install -g "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}" && npm cache clean --force
ENV DISABLE_AUTOUPDATER=1 \
    CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
WORKDIR /work
