# Ambiente de coleta (S02)

Issue #118 (papel B). Objetivo: o mesmo ambiente, verificável por script, nas três máquinas da coleta. Mudar versão de qualquer item depois da tag `protocolo-v1` é desvio (`desvios.md`).

## Estado da issue

| Item do checklist | Estado |
|---|---|
| Script de verificação do ambiente | feito: `harness/check-env` |
| Metadados gravados junto dos dados | feito: JSON em `results/ambiente-<máquina>-<data>.json` |
| Plano de execução sorteado com semente fixa | feito, **com número de cadeias provisório** (abaixo) |
| Ajustes do relatório do piloto | **bloqueado**: o piloto não foi executado e o relatório (#109) está sem dados e sem decisão |
| Mini-piloto | **bloqueado** pelo mesmo motivo; só se a decisão for GO com ajustes |
| Mesmas versões nas três máquinas | **não verificado**: o script existe, falta rodá-lo em cada máquina |
| Orçamento e limites do plano no dia | **pendente**: depende do consumo medido no piloto e da conferência no dia |
| Container sem acesso aos testes ocultos nas três máquinas | **parcial**: o `check-env` confere a pasta do workspace e o harness traz `container/verificar-imagem.sh`, mas o container nunca foi construído (Docker desligado) |
| Janela de poucos dias para a coleta | **pendente**: decisão do grupo |

O **piloto não foi executado** (não há `results/pilot/` nem relatório com dados). O harness agora existe (`harness/`, `docs/s01/harness.md`) e os testes de aceitação e a referência de P1 a P4 também (`docs/s01/testes-p1-p4.md`), mas nenhuma execução real do Claude Code foi feita. Por isso os ajustes pós-piloto e o mini-piloto continuam bloqueados: dependem do piloto e do relatório (#109) com decisão. Esta issue segue de `harness/check-env`, `harness/ambiente.pins` e `harness/plano_execucao.py`.

## Versões fixas

Definidas em `harness/ambiente.pins`, que é a fonte de verdade; esta tabela só a explica.

| Item | Valor | Origem |
|---|---|---|
| Claude Code | `2.1.238` | versão instalada na máquina do B; o grupo decidiu que ela serve só de **registro**, e que o que importa fixar é o modelo (`claude-sonnet-5-5`) |
| Modelo | `claude-sonnet-5-5` | protocolo congelado, seção 1 |
| Atualização automática | desativada (`DISABLE_AUTOUPDATER=1`) | protocolo congelado |
| Java | 21 | `seed/pom.xml` |
| ArchUnit | 1.3.0 | `seed/pom.xml` |
| PostgreSQL | imagem `postgres:16` | `seed/docker-compose.yml` |
| Maven | 3.9 | **proposta**: versão da máquina do B |
| Docker | 29 (versão maior) | **proposta**: versão da máquina do B |
| jdeps | 21 (vem com o JDK) | decorre do Java |
| Lizard | `1.26.1` | `requirements.txt` (instalar no `.venv`, ver abaixo) |
| jscpd | `5.4.3` | `npm install -g jscpd` na máquina do B |

"Proposta" quer dizer que o valor veio da máquina do B por falta de decisão do grupo; os outros dois precisam confirmar ou trocar. Lizard e jscpd foram fixados nas versões instaladas na máquina do B; os outros dois membros instalam as mesmas.

## Python do harness

O Python do sistema (Debian/Ubuntu) recusa `pip install` global. Use um ambiente virtual na pasta do laboratório (`.venv/` já está no `.gitignore`) e ative-o antes de rodar o harness e o `check-env`:

```bash
cd Laboratorio5
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt   # inclui lizard==1.26.1
source .venv/bin/activate
npm install -g jscpd@5.4.3
```

## Verificar o ambiente

```bash
cd Laboratorio5
cp .env.example .env && chmod 600 .env   # preencher a credencial; DISABLE_AUTOUPDATER e ANTHROPIC_MODEL já vêm no exemplo
harness/check-env --maquina A --workspace <pasta que o agente enxerga>
```

O script compara cada ferramenta com o pin, imprime `ok`, `DIVERGE` ou `SEM PIN`, grava o JSON de metadados (data UTC, máquina, host, commit, versões observadas) e sai com código 1 se algo divergir. Guarde o JSON junto dos dados da máquina. Com `--workspace`, falha se `tests/acceptance` ou `reference` estiver dentro da pasta do agente ou copiada nela.

Execução na máquina do B (primeira conferência, a título de exemplo do que o script pega):

| Item | Esperado | Observado | Estado |
|---|---|---|---|
| Modelo (`ANTHROPIC_MODEL`) | claude-sonnet-5-5 | não definido | diverge |
| Docker (daemon) | ativo | inativo | diverge |
| Lizard, jscpd | a decidir | não instalados | sem pin |
| Claude Code, Java, Maven, Docker, PostgreSQL, ArchUnit, jdeps, atualização automática | conforme pins | conformes | ok |

Ou seja, esta máquina **ainda não está pronta** para a coleta.

## Plano de execução

`docs/s02/plano-de-execucao.csv`: uma linha por cadeia, com modo (incremental ou regenerado), ordem dos pedidos (A ou B, do protocolo), máquina e posição na fila da máquina.

```bash
python -m harness.plano_execucao --cadeias-por-modo 12 --semente 118
```

- **Balanceado:** cada combinação modo × ordem × máquina recebe o mesmo número de cadeias (exige múltiplo de 6 por modo). O arquivo atual tem 12 por modo, 24 no total, 2 por combinação.
- **Reprodutível:** o sorteio ordena por SHA-256 de `semente:chave`, sem depender do `random` do Python, então qualquer máquina regenera o mesmo arquivo. Semente fixa: `118`.
- **Fila por máquina misturada:** modos e ordens se alternam em cada máquina, para uma deriva do ambiente não coincidir com um modo.
- **Número de cadeias é provisório.** A issue #119 diz de 10 a 15 por modo; a simulação de poder (`simulacao-de-poder.md`) indica cerca de 15 a 20 para um efeito médio. Com o balanceamento exato os valores possíveis são 12 ou 18. Escolhi 12 só para o arquivo existir; se o grupo preferir 18, basta regerar com a mesma semente. Decisão pendente do grupo, e o protocolo congelado (seção 3) ainda tem esse número em branco.

## Variáveis e limites

| Variável | Valor | Para quê |
|---|---|---|
| `CLAUDE_CODE_OAUTH_TOKEN` ou `ANTHROPIC_API_KEY` | em `Laboratorio5/.env` (não versionado; modelo em `.env.example`) | credencial do agente; nunca no repositório |
| `DISABLE_AUTOUPDATER` | `1` | impede troca de versão do Claude Code durante a janela |
| `ANTHROPIC_MODEL` | `claude-sonnet-5-5` | modelo fixo |
| `BASE_URL` | `http://localhost:8080` | alvo dos testes de regressão e aceitação |
| `STUB_PORTA` | `9099` | stub de P9 |
| `NOTIFICACAO_URL` | `http://host:9099/notificacoes` | serviço externo simulado de P9 |
| `DATABASE_URL` | definida pelo `docker compose` | única configuração de banco da semente |

Limites de turnos e de tempo por passo, orçamento por cadeia e janela da coleta ainda estão em aberto no protocolo (seção 1) e dependem do consumo do piloto. Devem ser preenchidos aqui e no protocolo antes da tag `protocolo-v1`.

## Antes de iniciar a coleta

1. Grupo decide Lizard, jscpd, Maven e Docker e preenche `harness/ambiente.pins`.
2. Cada máquina roda `harness/check-env --maquina <A|B|C> --workspace ...` e termina com "ambiente conforme".
3. Relatório do piloto com decisão; ajustes aplicados (e mini-piloto, se GO com ajustes).
4. Um passo de ponta a ponta rodado igual nas três máquinas (o harness existe, mas nunca rodou com o Claude Code de verdade).
5. Número de cadeias fixado e plano regerado; orçamento conferido no dia.
6. Tag `protocolo-v1`.
