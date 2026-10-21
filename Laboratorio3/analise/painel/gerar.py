"""Gera `dashboard/`: index.html estático e os CSVs de `dashboard/data/`.

Uso: python -m analise.painel   (ou `make dashboard`)

Roda depois de `make reproduce`, porque lê as tabelas de `analise/saida/`. O resultado é versionado:
o GitHub Pages serve a pasta direto do repositório.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from analise.comum import RAIZ
from analise.painel import conteudo
from analise.painel.dados import DERIVADOS, FONTES, derivados

ESTATICO = Path(__file__).resolve().parent / "estatico"
DESTINO = RAIZ / "dashboard"
D3 = ("https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js",
      "sha384-CjloA8y00+1SDAUkjs099PVfnY2KmDC2BZnws9kh8D/lX1s46w6EPhpXdqMfjK6i")
FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Crect width='16' "
           "height='16' rx='3' fill='%234C72B0'/%3E%3Cpath d='M3 11l3-4 3 2 4-5' stroke='white' stroke-width='1.6' "
           "fill='none' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E")


def _ler(nome: str) -> str:
    return (ESTATICO / nome).read_text(encoding="utf-8")


def pagina() -> str:
    ids = ", ".join(f'"{i}"' for i in FONTES)
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Painel DORA Lab03</title>
<meta name="description" content="Hipóteses, resultados e conclusões das perguntas de pesquisa do Lab03, sobre métricas DORA em repositórios open-source.">
<link rel="icon" href="{FAVICON}">
<style>
{_ler("tokens.css")}
{_ler("page.css")}
</style>
</head>
<body>
<div id="dash-root">
<div class="px">
  <div class="px-top">
    <h1 class="px-title">{conteudo.titulo_html()}</h1>
    <p class="px-lede">Uma aba por pergunta de pesquisa: a hipótese, o que os dados mostram e a conclusão. A cor do ponto em cada aba indica se a hipótese se confirmou, se confirmou em parte ou se foi refutada.</p>
  </div>
  <nav class="px-tabs" role="tablist" aria-label="Perguntas de pesquisa">{conteudo.navegacao()}</nav>
  <div id="px-pages"></div>
  <p class="px-rodape">Página estática gerada por <code>python -m analise.painel</code> a partir dos CSVs do repositório. As hipóteses estão em <code>docs/hipoteses.md</code>. Os vereditos e as conclusões são uma leitura dos dados, em rascunho para a seção de Resultados e Discussão do artigo.</p>
</div>
</div>
{conteudo.PAGINAS}
<script src="{D3[0]}" integrity="{D3[1]}" crossorigin="anonymous"></script>
<script>
{_ler("shim.js")}
</script>
<script>
{_ler("page.js")}
</script>
<script>dash.carregar([{ids}]);</script>
</body>
</html>
"""


def construir(destino: Path = DESTINO) -> list[Path]:
    """Escreve index.html e data/*.csv em `destino`. Devolve o que escreveu."""
    dados = destino / "data"
    dados.mkdir(parents=True, exist_ok=True)
    escritos: list[Path] = []
    derivado = derivados()
    for i, (arquivo, _, _) in FONTES.items():
        alvo = dados / f"{i}.csv"
        if arquivo is None:
            derivado[i].to_csv(alvo, index=False, lineterminator="\n")
        else:
            alvo.write_bytes((RAIZ / arquivo).read_bytes().replace(b"\r\n", b"\n"))
        escritos.append(alvo)
    assert set(DERIVADOS) == set(derivado), "um conjunto derivado ficou sem gerar"
    html = destino / "index.html"
    html.write_text(pagina(), encoding="utf-8", newline="\n")
    escritos.append(html)
    return escritos


def main() -> None:
    escritos = construir()
    print(f"painel gerado em {DESTINO} ({len(escritos)} arquivos)")
