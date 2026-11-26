#!/usr/bin/env bash
# Constroi a imagem do agente com a versao do Claude Code fixada em harness/ambiente.pins.
set -euo pipefail
aqui="$(cd "$(dirname "$0")" && pwd)"
versao="$(sed -n 's/^CLAUDE_CODE=//p' "$aqui/../ambiente.pins")"
[ -n "$versao" ] || { echo "CLAUDE_CODE vazio em ambiente.pins" >&2; exit 1; }
docker build --build-arg "CLAUDE_CODE_VERSION=$versao" -t "lab05-agente:$versao" "$aqui"
echo "imagem: lab05-agente:$versao"
