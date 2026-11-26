#!/usr/bin/env bash
# Roda os testes de aceitacao ocultos (P5 a P10) e, opcionalmente, a regressao.
#
# Uso:
#   ./rodar.sh                          sobe reference/ com H2, roda P1..P10 duas vezes
#   ./rodar.sh --pedidos "P5 P7"        so alguns pedidos
#   ./rodar.sh --regressao              inclui tests/regression antes das rodadas
#   ./rodar.sh --rodadas 3              numero de rodadas na MESMA instancia da aplicacao
#   ./rodar.sh --externo                nao sobe nada: usa a aplicacao ja no ar em BASE_URL
#                                       (ex.: docker compose up do PostgreSQL; ver docs/s02/testes-p5-p10.md)
#
# Variaveis: BASE_URL (padrao http://localhost:8080), STUB_PORTA (padrao 9099).
# Estes testes e reference/ ficam FORA do workspace do agente: nunca monte esta pasta no container.
set -euo pipefail

aqui="$(cd "$(dirname "$0")" && pwd)"
lab="$(cd "$aqui/../.." && pwd)"
pedidos="P1 P2 P3 P4 P5 P6 P7 P8 P9 P10"
rodadas=2
regressao=0
externo=0

while [ $# -gt 0 ]; do
  case "$1" in
    --pedidos) pedidos="$2"; shift 2 ;;
    --rodadas) rodadas="$2"; shift 2 ;;
    --regressao) regressao=1; shift ;;
    --externo) externo=1; shift ;;
    *) echo "argumento desconhecido: $1" >&2; exit 2 ;;
  esac
done

export BASE_URL="${BASE_URL:-http://localhost:8080}"
export STUB_PORTA="${STUB_PORTA:-9099}"
pid_app=""

parar() {
  if [ -n "$pid_app" ]; then kill "$pid_app" 2>/dev/null || true; fi
}
trap parar EXIT

if [ "$externo" -eq 0 ]; then
  if curl -s -o /dev/null "$BASE_URL/health"; then
    echo "ja existe uma aplicacao em $BASE_URL; pare-a ou use --externo" >&2
    exit 2
  fi
  (cd "$lab/reference" && mvn -B -q -DskipTests package)
  SPRING_PROFILES_ACTIVE=h2 \
  NOTIFICACAO_URL="http://localhost:${STUB_PORTA}/notificacoes" \
    java -jar "$lab/reference/target/semente.jar" >"${TMPDIR:-/tmp}/reference.log" 2>&1 &
  pid_app=$!
fi

for _ in $(seq 1 60); do
  [ "$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/health" || true)" = "200" ] && break
  sleep 1
done
[ "$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/health" || true)" = "200" ] || { echo "aplicacao nao ficou pronta" >&2; exit 1; }

if [ "$regressao" -eq 1 ]; then
  echo "== regressao"
  (cd "$lab/tests/regression" && mvn -B -q test)
fi

filtro=""
for p in $pedidos; do
  numero="${p#P}"
  filtro="${filtro:+$filtro,}**/p${numero}/*Test"
done

for r in $(seq 1 "$rodadas"); do
  echo "== rodada $r de $rodadas: $pedidos"
  saida="$(cd "$aqui" && mvn -B test -Dtest="$filtro" -Dsurefire.failIfNoSpecifiedTests=false 2>&1)" || {
    echo "$saida" | grep -E 'Tests run:|FAIL|ERROR\]' | head -30
    exit 1
  }
  resumo="$(echo "$saida" | grep -E '^\[INFO\] Tests run:' | tail -1)"
  echo "$resumo"
  # um filtro que nao seleciona nada passaria em silencio: exige ao menos um teste executado
  echo "$resumo" | grep -Eq 'Tests run: [1-9]' || { echo "nenhum teste executado" >&2; exit 1; }
done
echo "== ok: $rodadas rodadas verdes ($pedidos)"
