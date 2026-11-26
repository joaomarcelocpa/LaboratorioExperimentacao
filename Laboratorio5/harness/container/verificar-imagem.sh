#!/usr/bin/env bash
# Confere a imagem do agente: versao exata do Claude Code, sem atualizacao automatica e SEM os testes ocultos.
# Rode em cada uma das tres maquinas antes da coleta.
set -uo pipefail
aqui="$(cd "$(dirname "$0")" && pwd)"
versao="$(sed -n 's/^CLAUDE_CODE=//p' "$aqui/../ambiente.pins")"
img="lab05-agente:$versao"
falhas=0

obtida="$(docker run --rm "$img" claude --version | awk '{print $1}')"
if [ "$obtida" = "$versao" ]; then echo "ok   versao $obtida"; else echo "FALHA versao: $obtida != $versao"; falhas=1; fi

if [ "$(docker run --rm "$img" printenv DISABLE_AUTOUPDATER)" = "1" ]; then
  echo "ok   atualizacao automatica desativada"
else
  echo "FALHA atualizacao automatica"; falhas=1
fi

# O container monta so o workspace: as pastas ocultas do laboratorio nao podem existir em lugar nenhum dele.
achou="$(docker run --rm "$img" sh -c 'find / -xdev -type d \( -name acceptance -o -name reference \) -path "*Laboratorio5*" 2>/dev/null | head -1')"
if [ -z "$achou" ]; then echo "ok   sem testes ocultos no container"; else echo "FALHA: $achou"; falhas=1; fi
exit $falhas
