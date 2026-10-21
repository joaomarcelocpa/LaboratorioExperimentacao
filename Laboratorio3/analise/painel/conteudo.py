"""Conteúdo das abas do painel: hipótese, vereditos, gráficos e conclusão de cada RQ.

Todo número da página é uma marca (`data-source`, `data-where`, `data-field`, `data-fmt`) ligada a um
conjunto de `analise/painel/dados.py`; o JavaScript preenche cada marca a partir do CSV. Os textos são
a leitura dos dados e podem ser reescritos aqui, sem mexer nos números.
"""
from __future__ import annotations

from analise.painel.dados import FONTES


# ---------- marcas: todo número vem de um conjunto de dados ----------------------------------------------
def V(src, field, fmt, where=None):
    w = f' data-where="{where}"' if where else ""
    return f'<span class="v" data-source="{src}"{w} data-field="{field}" data-fmt="{fmt}">—</span>'


def OBS(i, fmt):
    return V("observados", "valor", fmt, f"id={i}")


def MED(metrica, field, fmt):
    return V("medianas", field, fmt, f"metrica={metrica}")


def F6(fator, metrica, field, fmt):
    return V("rq06_fatores", field, fmt, f"fator={fator}&amp;metrica={metrica}")


def GR(fator, grupo, field, fmt):
    return V("rq06_grupos", field, fmt, f"fator={fator}&amp;grupo={grupo}")


def PAR(par, field, fmt):
    return V("rq07_pares", field, fmt, f"par={par}")


def R8(metrica, field, fmt):
    return V("rq08b_resumo", field, fmt, f"metrica={metrica}")


CHIPS = {"ok": ("px-ok", "Confirmada"), "par": ("px-par", "Parcial"), "bad": ("px-bad", "Refutada"),
         "nt": ("px-nt", "Não testável"), "nao": ("px-nt", "Não testada")}


def chip(kind, big=False):
    c, t = CHIPS[kind]
    return f'<span class="px-chip {c}{" px-big" if big else ""}">{t}</span>'


def kpi(label, value, sub=""):
    s = f'<span class="s">{sub}</span>' if sub else ""
    return f'<div class="px-kpi"><span class="l">{label}</span><span class="n">{value}</span>{s}</div>'


def kpis(*items):
    return f'<div class="px-kpis">{"".join(items)}</div>'


def chart(title, note, chart_kind, source, **attrs):
    a = "".join(f' data-{k.replace("_", "-")}="{v}"' for k, v in attrs.items())
    n = f'<p class="note">{note}</p>' if note else ""
    return (f'<article class="px-card"><h3>{title}</h3>{n}'
            f'<div class="px-chart" data-chart="{chart_kind}" data-source="{source}"{a}></div></article>')


def grid(*cards):
    return f'<div class="px-grid">{"".join(cards)}</div>'


def head(eyebrow, question, kind, sub):
    return (f'<header class="px-head"><div><p class="px-eyebrow">{eyebrow}</p><h2 class="px-q">{question}</h2></div>'
            f'<div class="px-verd">{chip(kind, True)}<small>{sub}</small></div></header>')


def hyp(blocks, prov_ok=True):
    """blocks: lista de (rótulo, texto). prov_ok: hipótese escrita antes dos dados."""
    prov = ('<span class="px-chip px-ok px-prov">Escrita antes dos dados</span>' if prov_ok
            else '<span class="px-chip px-par px-prov">Registrada depois da coleta</span>')
    bq = "".join(f"<p>{t}</p>" for t in blocks)
    return f'<article class="px-card px-hip"><h3>Hipótese</h3>{prov}<blockquote>{bq}</blockquote></article>'


def claims(rows):
    body = "".join(f'<tr><td>{h}</td><td class="c-o">{o}</td><td>{chip(k)}</td></tr>' for h, o, k in rows)
    return ('<article class="px-card"><h3>O que os dados mostram</h3><div class="px-tablewrap"><table class="px-claims">'
            '<thead><tr><th>Hipótese</th><th>Observado</th><th>Veredito</th></tr></thead>'
            f'<tbody>{body}</tbody></table></div></article>')


def concl(bullets, limites):
    b = "".join(f"<li>{x}</li>" for x in bullets)
    l = "".join(f"<li>{x}</li>" for x in limites)
    return (f'<article class="px-card px-concl"><h3>Conclusão</h3><ul>{b}</ul>'
            f'<div class="lim"><b>Limitações</b><ul>{l}</ul></div></article>')


def page(pid, *parts):
    return f'<template id="tpl-{pid}">{"".join(parts)}</template>'


def two(a, b):
    return f'<div class="px-two">{a}{b}</div>'


BASE_GH = "https://github.com/joaomarcelocpa/LaboratorioExperimentacao/blob/main/Laboratorio3/"


def fontes_card() -> str:
    linhas = "".join(
        f'<tr><td>{tit}</td><td>{desc}</td><td>'
        + (f'<a href="{BASE_GH}{arq}">{arq}</a>' if arq else "calculado de <code>metricas.csv</code> e das tabelas")
        + "</td></tr>"
        for _, (arq, tit, desc) in FONTES.items())
    return ('<article class="px-card"><h3>De onde vêm os números</h3>'
            '<p class="note">Cada número da página é lido de um destes CSVs, que ficam em <code>dashboard/data/</code>. '
            'Os calculados para o painel (<code>python -m analise.painel</code>) dizem a conta em <code>observados.csv</code>.</p>'
            '<div class="px-tablewrap"><table class="px-score"><thead><tr><th>Conjunto</th><th>O que é</th><th>Origem no repositório</th></tr></thead>'
            f'<tbody>{linhas}</tbody></table></div></article>')


# =====================================================================================================
# Visão geral
# =====================================================================================================
def score_row(go, nome, hip, kind, achado):
    return (f'<tr><td><button type="button" class="go" data-go="{go}">{nome}</button></td><td>{hip}</td>'
            f'<td>{chip(kind)}</td><td>{achado}</td></tr>')


geral = page(
    "geral",
    kpis(
        kpi("Repositórios analisados", OBS("n_repos", "int"), "do GitHub, com 5+ releases e 50+ runs de CI na janela"),
        kpi("Janela de observação", '<span class="v">12 meses</span>', "de 1/out/2025 a 30/set/2026"),
        kpi("Classe DORA Elite (C1)", V("classes_c1", "repositorios", "int", "classe=Elite"),
            V("classes_c1", "pct", "pct0", "classe=Elite") + " da amostra"),
        kpi("Concordância na conferência manual", V("kappa", "kappa", "d2", "dimensao=corretiva"),
            "κ de Fleiss, release corretiva"),
    ),
    '<article class="px-card"><h3>Hipóteses e vereditos</h3>'
    '<p class="note">Cada linha leva à aba da pergunta. O veredito compara a hipótese registrada no repositório com o que os dados mostram.</p>'
    '<div class="px-tablewrap"><table class="px-score"><thead><tr><th>Pergunta</th><th>Hipótese</th><th>Veredito</th><th>Principal achado</th></tr></thead><tbody>'
    + score_row("rq01", "RQ 01 · Frequência", "Mediana entre 0,25 e 1 release por semana; poucos repositórios Elite", "ok",
                f"mediana de {MED('freq_release', 'mediana', 'd2')} por semana; {OBS('rq01_n_elite', 'int')} Elite")
    + score_row("rq02", "RQ 02 · Lead time", "Mediana de 1 a 7 dias; variante por commit menor que por release", "par",
                f"mediana de {OBS('rq02_mediana_dias', 'd1')} dias (acima de 7)")
    + score_row("rq03", "RQ 03 · Taxa de falha", "CFR de CI entre 10% e 25%; CFR por release abaixo de 30%", "bad",
                f"CFR de CI de {MED('cfr_a', 'mediana', 'pct1')}; por release, {MED('cfr_b', 'mediana', 'pct1')}")
    + score_row("rq04", "RQ 04 · Recuperação", "Mediana abaixo de 1 dia, com cauda longa e censura relevante", "par",
                f"mediana de {MED('recuperacao_h', 'mediana', 'h1')} h; {OBS('rq04_pct_eps_censurados', 'pct1')} dos episódios censurados")
    + score_row("rq05", "RQ 05 · Velocidade × estabilidade", "Correlação fraca e negativa entre frequência e CFR", "par",
                f"ρ = {V('rq05_spearman', 'rho', 's2', 'variante=cfr_a')} com o CFR (a); {V('rq05_spearman', 'rho', 's2', 'variante=cfr_b')} com o (b)")
    + score_row("rq06", "RQ 06 · Fatores", "Associações fracas; poucos testes significativos após Holm", "par",
                f"{OBS('rq06_sig_holm', 'int')} de {OBS('rq06_n_testes', 'int')} testes significativos; idade com ε² até {F6('idade_q', 'cfr_b', 'epsilon2', 'd2')}")
    + score_row("rq07", "RQ 07 · Sensibilidade", "30% a 50% mudam de classe; kappa entre 0,3 e 0,6", "par",
                f"{OBS('rq07_pct_mudou_algum', 'pct1')} mudam de classe em algum par; kappa de {PAR('C1xC2', 'kappa', 'd2')} a {PAR('C1xC3', 'kappa', 'd2')}")
    + score_row("rq08", "RQ 08 · Bônus", "08a: rework maior que o CFR (b). 08b: maioria sem tendência", "par",
                f"{R8('cfr_a', 'pct_sem_tendencia', 'pct1')} dos repositórios sem tendência no CFR de CI")
    + '</tbody></table></div></article>',
    grid(
        chart("Funil de seleção", "De todos os candidatos da busca até a amostra.", "funnel", "funil"),
        chart("Classe DORA de referência (C1)", "Release como deploy, lead time (a) e CFR (a); a classe é a mediana das quatro notas.", "classes", "classes_c1"),
    ),
    grid(
        chart("Concordância entre os avaliadores", "Três pessoas rotularam 60 repositórios e 300 releases, cada uma sem ver as respostas das outras nem a saída da heurística.", "bars", "kappa", preset="kappa"),
        '<article class="px-card"><h3>Como ler este painel</h3>'
        '<p class="note">Os números vêm dos CSVs gerados pelo pipeline, e a conclusão de cada aba é uma leitura desses números.</p>'
        f'<ul style="margin:0;padding-left:1.1rem;display:flex;flex-direction:column;gap:6px;line-height:1.5">'
        f'<li><b>Confirmada:</b> {chip("ok")} o que a hipótese afirmava aparece nos dados.</li>'
        f'<li><b>Parcial:</b> {chip("par")} parte da hipótese se sustenta e parte não.</li>'
        f'<li><b>Refutada:</b> {chip("bad")} os dados contradizem a hipótese.</li>'
        f'<li><b>Não testável ou não testada:</b> {chip("nt")} faltam dados, ou a análise não cobriu esse ponto.</li></ul>'
        '<p class="note"><b>Origem das hipóteses.</b> As das RQ 01, 02, 03b, 06, 07 e 08a foram escritas antes de qualquer análise. '
        'As das RQ 03a, 04, 05 e 08b foram registradas depois da coleta, a partir das hipóteses informais do plano, sem ajuste aos resultados; '
        'isso entra como ameaça à validade.</p></article>',
    ),
    fontes_card(),
)

# =====================================================================================================
# RQ 01
# =====================================================================================================
rq01 = page(
    "rq01",
    head("RQ 01 · responsável: A", "Qual a frequência de deploys dos repositórios populares que usam CI/CD?", "ok",
         "todas as afirmações se confirmam"),
    kpis(
        kpi("Mediana", MED("freq_release", "mediana", "d2"), f"releases por semana; IQR de {MED('freq_release', 'q1', 'd2')} a {MED('freq_release', 'q3', 'd2')}"),
        kpi("Média", MED("freq_release", "media", "d2"), "puxada por poucos repositórios muito frequentes"),
        kpi("Repositórios Elite", OBS("rq01_n_elite", "int"), "7 ou mais releases por semana"),
        kpi("Tags ≥ releases", OBS("rq01_pct_tag_ge_release", "pct1"), "dos repositórios têm mais tags que releases"),
    ),
    two(
        hyp(["A mediana de releases por semana ficará entre 0,25 e 1, ou seja, entre Medium e High na tabela de referência. Poucos repositórios chegarão a Elite (7 ou mais por semana).",
             "Esperamos uma distribuição muito assimétrica à direita, com a média bem acima da mediana.",
             "A contagem por tag deve render frequência maior ou igual à por release."]),
        claims([
            ("Mediana entre 0,25 e 1 release por semana", f"Mediana de {MED('freq_release', 'mediana', 'd2')}, com IQR de {MED('freq_release', 'q1', 'd2')} a {MED('freq_release', 'q3', 'd2')}.", "ok"),
            ("Poucos repositórios Elite (7 ou mais por semana)", f"{OBS('rq01_n_elite', 'int')} de {OBS('n_repos', 'int')} ({V('rq01_faixas', 'pct', 'pct1', 'faixa=Elite (≥ 7/sem)')}).", "ok"),
            ("Distribuição assimétrica à direita, média acima da mediana", f"Média de {MED('freq_release', 'media', 'd2')} contra mediana de {MED('freq_release', 'mediana', 'd2')}.", "ok"),
            ("Frequência por tag maior ou igual à por release", f"Mediana por tag de {MED('freq_tag', 'mediana', 'd2')}; {OBS('rq01_pct_tag_ge_release', 'pct1')} dos repositórios com tag ≥ release.", "ok"),
        ]),
    ),
    grid(
        chart("Distribuição da frequência", "Cada barra reúne repositórios com frequência parecida. Os fundos cinza marcam as faixas DORA.", "hist", "metricas", preset="freq"),
        chart("Repositórios por faixa DORA", "A maioria se divide entre Medium e Low.", "bars", "rq01_faixas", preset="faixas"),
        chart("A definição de deploy muda a mediana?", "Pré-releases e tags aumentam a frequência, mas a mediana não muda de faixa.", "bars", "medianas", preset="freq_variantes"),
    ),
    concl(
        [f"O ritmo típico é de um ciclo a cada três semanas: mediana de {MED('freq_release', 'mediana', 'd2')} releases por semana, e metade dos repositórios entre {MED('freq_release', 'q1', 'd2')} e {MED('freq_release', 'q3', 'd2')}.",
         f"Quase não há entrega contínua. Só {OBS('rq01_n_elite', 'int')} repositórios chegam a Elite, enquanto {V('rq01_faixas', 'pct', 'pct0', 'faixa=Medium (1/mês a 1/sem)')} ficam em Medium e {V('rq01_faixas', 'pct', 'pct0', 'faixa=Low (< 1/mês)')} em Low (menos de uma release por mês).",
         f"A média ({MED('freq_release', 'media', 'd2')}) é mais que o dobro da mediana: poucos repositórios que publicam quase todo dia puxam o valor para cima. Por isso o painel mostra mediana e IQR.",
         f"Contar pré-releases ({MED('freq_release_pre', 'mediana', 'd2')}) ou tags ({MED('freq_tag', 'mediana', 'd2')}) sobe a mediana, mas ela continua na faixa Medium."],
        ["Release publicada é um proxy de deploy: subestima serviços que fazem deploy contínuo sem publicar release e superestima bibliotecas com releases automáticas.",
         "A amostra exige pelo menos 5 releases na janela, o que já exclui projetos que publicam pouco."],
    ),
)

# =====================================================================================================
# RQ 02
# =====================================================================================================
rq02 = page(
    "rq02",
    head("RQ 02 · responsável: B", "Qual o tempo entre um commit e seu respectivo deploy?", "par", "o nível erra, a direção acerta"),
    kpis(
        kpi("Lead time (a), por release", OBS("rq02_mediana_dias", "d1"), "dias, mediana entre repositórios"),
        kpi("Lead time (b), por commit", MED("lt_commit_h", "mediana", "dias1"), "dias, mediana entre repositórios"),
        kpi("Entre 1 e 7 dias", OBS("rq02_pct_1a7d", "pct1"), "dos repositórios, o intervalo da hipótese"),
        kpi("(a) maior que (b)", OBS("rq02_pct_a_maior_b", "pct1"), "dos repositórios"),
    ),
    two(
        hyp(["Repositórios populares open-source apresentam mediana de lead time entre 1 e 7 dias (categoria High na escala DORA).",
             "A variante por commit (b) deverá ser menor que a variante por release (a), pois commits recentes puxam a mediana para baixo enquanto um único commit antigo inflaciona apenas a variante (a)."]),
        claims([
            ("Mediana de lead time entre 1 e 7 dias (High)", f"Mediana de {OBS('rq02_mediana_dias', 'd1')} dias por release: acima de 7, na faixa Medium. Só {OBS('rq02_pct_1a7d', 'pct1')} dos repositórios estão entre 1 e 7 dias.", "bad"),
            ("Variante (b) por commit menor que (a) por release", f"{MED('lt_commit_h', 'mediana', 'h1')} h contra {MED('lt_release_h', 'mediana', 'h1')} h, diferença de {OBS('rq02_dif_pct', 'pct1')} na mediana; (a) é maior em {OBS('rq02_pct_a_maior_b', 'pct1')} dos repositórios.", "ok"),
        ]),
    ),
    grid(
        chart("Distribuição do lead time", "Cada variante tem uma linha de mediana. Os fundos cinza marcam as faixas DORA (1 dia, 7 dias e 30 dias).", "hist", "metricas", preset="lt"),
        chart("Mediana por variante", "Tirar commits de bots reduz pouco o valor.", "bars", "medianas", preset="lt_medianas"),
    ),
    concl(
        [f"O tempo típico entre o commit e a release é de {OBS('rq02_mediana_dias', 'd1')} dias, o que coloca o lead time na faixa Medium (1 semana a 30 dias), uma faixa abaixo do previsto.",
         f"As duas variantes quase coincidem no valor típico ({MED('lt_release_h', 'mediana', 'h1')} h e {MED('lt_commit_h', 'mediana', 'h1')} h), embora (a) seja a maior em {OBS('rq02_pct_a_maior_b', 'pct1')} dos repositórios. A diferença esperada entre elas aparece pouco na mediana.",
         f"Excluir commits de bots leva a mediana por commit a {MED('lt_commit_sem_bots_h', 'mediana', 'h1')} h: o efeito é pequeno."],
        ["A mediana por commit reflete commits antigos quando a base do primeiro compare é uma release de anos atrás, o que acontece em repositórios que só recentemente passaram a usar Releases do GitHub.",
         "A data do commit é author.date, que rebase e squash merge podem distorcer."],
    ),
)

# =====================================================================================================
# RQ 03
# =====================================================================================================
rq03 = page(
    "rq03",
    head("RQ 03 · responsáveis: C (03a) e B (03b)", "Qual a taxa de falha das mudanças entregues por esses repositórios?", "bad",
         "as duas faixas previstas ficam longe"),
    kpis(
        kpi("CFR de CI (a)", MED("cfr_a", "mediana", "pct1"), "mediana: falhas ÷ (falhas + sucessos)"),
        kpi("CFR por release (b)", MED("cfr_b", "mediana", "pct1"), "mediana: releases seguidas de corretiva em 7 dias"),
        kpi("CFR por issues (c)", MED("cfr_c", "mediana", "pct1"), f"mediana, em {MED('cfr_c', 'n', 'int')} repositórios com issues de bug"),
        kpi("Precisão da heurística (b)", V("heuristica_f1", "precisao", "d2", "variante=v5"), "contra a amostra rotulada à mão"),
    ),
    two(
        hyp(["<b>03a (C).</b> A mediana da taxa de falha das execuções de CI no default branch ficará entre 10% e 25%. Esperamos que a taxa caia de forma perceptível quando desconsideramos as falhas seguidas de sucesso no mesmo commit (flaky), e que esse proxy superestime a taxa de falha em produção.",
             "<b>03b (B).</b> A maioria dos repositórios terá CFR por release abaixo de 30% (faixa High), com mediana próxima de 15%. Projetos com maior frequência de releases devem ter CFR (b) mais baixo."],
            prov_ok=False),
        claims([
            ("03a · Mediana do CFR de CI entre 10% e 25%", f"Mediana de {MED('cfr_a', 'mediana', 'pct1')}. {OBS('rq03a_pct_abaixo10', 'pct1')} dos repositórios estão abaixo de 10%, e só {OBS('rq03a_pct_10a25', 'pct1')} na faixa prevista.", "bad"),
            ("03a · A taxa cai de forma perceptível sem as falhas flaky", f"Mediana do CFR bruto de {MED('cfr_a_bruto', 'mediana', 'pct1')} passa a {MED('cfr_a_sem_flaky', 'mediana', 'pct1')}, queda de {OBS('rq03a_queda_flaky_pp', 'pp1')} (as falhas flaky são {MED('pct_falhas_flaky', 'mediana', 'pct1')} das falhas, na mediana).", "par"),
            ("03a · O CI superestima a falha em produção", "Sem dados de produção, não há como medir essa diferença.", "nt"),
            ("03b · Maioria com CFR (b) abaixo de 30%, mediana perto de 15%", f"Mediana de {MED('cfr_b', 'mediana', 'pct1')}. Só {OBS('rq03b_pct_abaixo30', 'pct1')} dos repositórios ficam abaixo de 30%.", "bad"),
            ("03b · Mais releases por semana, CFR (b) mais baixo", f"ρ = {V('rq05_spearman', 'rho', 's2', 'variante=cfr_b')} (p &lt; 0,001): o contrário, mais frequência vem com CFR (b) mais alto.", "bad"),
        ]),
    ),
    grid(
        chart("CFR de CI (a)", "Falhas de pipeline no default branch. Os fundos cinza marcam as faixas DORA do CFR (15%, 30% e 45%).", "hist", "metricas", preset="cfra"),
        chart("CFR por release (b)", "Releases seguidas de uma corretiva em até 7 dias, pela heurística v5.", "hist", "metricas", preset="cfrb"),
    ),
    grid(
        chart("As três versões do CFR (a)", "Remover falhas flaky muda pouco a mediana.", "bars", "medianas", preset="cfr_variantes"),
        chart("Heurística da release corretiva", "F1 de cada versão contra a conferência manual. Nenhuma chega a 0,70.", "bars", "heuristica_f1", preset="heuristica"),
    ),
    concl(
        [f"A falha de CI é rara: mediana de {MED('cfr_a', 'mediana', 'pct1')}, faixa Elite (até 15%). {OBS('rq03a_pct_abaixo10', 'pct1')} dos repositórios têm menos de 10%, e as falhas flaky explicam pouco (removê-las muda a mediana em {OBS('rq03a_queda_flaky_pp', 'pp1')}).",
         f"O CFR por release é muito maior ({MED('cfr_b', 'mediana', 'pct1')}, faixa Medium), e esse número é frágil. A heurística adotada (v5) tem precisão de {V('heuristica_f1', 'precisao', 'd2', 'variante=v5')} e F1 de {V('heuristica_f1', 'f1', 'd2', 'variante=v5')}, abaixo do limiar de 0,70 do enunciado, e a concordância entre os avaliadores na dimensão corretiva é κ = {V('kappa', 'kappa', 'd2', 'dimensao=corretiva')}. O (b) deve ser lido como um limite superior.",
         f"A hipótese da 03b falha no nível (mediana) e na direção (ρ positivo). Essa relação positiva entre frequência e CFR (b) é provavelmente em parte mecânica, como discute a RQ 05."],
        ["O CFR de CI mede falha de pipeline, e não de produção.",
         f"O CFR (c), por issues de bug, existe só em {MED('cfr_c', 'n', 'int')} repositórios: os demais não têm issues com os labels buscados.",
         "As hipóteses 03a foram registradas depois da coleta."],
    ),
)

# =====================================================================================================
# RQ 04
# =====================================================================================================
rq04 = page(
    "rq04",
    head("RQ 04 · responsável: C", "Qual o tempo de recuperação após uma execução de CI/CD com falha?", "par", "o nível confirma, a censura e o flaky não"),
    kpis(
        kpi("Mediana de recuperação", MED("recuperacao_h", "mediana", "h1"), f"horas; IQR de {MED('recuperacao_h', 'q1', 'h1')} a {MED('recuperacao_h', 'q3', 'h1')}"),
        kpi("Em High (1 h a 1 dia)", OBS("rq04_pct_high", "pct0"), f"dos {OBS('rq04_n_repos', 'int')} repositórios com episódios"),
        kpi("Mediana de 1 semana ou mais", OBS("rq04_repos_acima_1sem", "int"), "repositórios com CI quebrado por semanas"),
        kpi("Episódios censurados", OBS("rq04_pct_eps_censurados", "pct1"), f"{OBS('rq04_eps_censurados', 'int')} de {OBS('rq04_n_eps', 'int')} episódios"),
    ),
    two(
        hyp(["A mediana do tempo de recuperação após uma falha de CI ficará abaixo de um dia, o que colocaria a maior parte dos repositórios na faixa High.",
             "Esperamos uma cauda longa: alguns repositórios devem conviver com workflows quebrados por semanas, e uma parcela não desprezível dos episódios deve terminar censurada no fim da janela.",
             "Ao excluir os episódios compostos apenas de falhas instáveis, esperamos que a mediana aumente."], prov_ok=False),
        claims([
            ("Mediana abaixo de 1 dia, maior parte em High", f"Mediana de {MED('recuperacao_h', 'mediana', 'h1')} h. {OBS('rq04_pct_high', 'pct0')} dos repositórios ficam em High e a maioria do restante em Elite.", "ok"),
            ("Cauda longa, com falhas por semanas", f"{OBS('rq04_repos_acima_1sem', 'int')} repositórios com mediana de 1 semana ou mais e {OBS('rq04_repos_acima_1dia', 'int')} acima de 1 dia; o p90 é de {MED('recuperacao_h', 'p90', 'h1')} h.", "ok"),
            ("Parcela não desprezível de episódios censurada", f"{OBS('rq04_eps_censurados', 'int')} de {OBS('rq04_n_eps', 'int')} episódios ({OBS('rq04_pct_eps_censurados', 'pct1')}). {OBS('rq04_repos_com_censura', 'int')} repositórios têm ao menos um.", "bad"),
            ("Excluir episódios só de flaky aumenta a mediana", f"Só {OBS('rq04_eps_so_flaky', 'int')} episódios são só de flaky. A mediana de {MED('recuperacao_h', 'mediana', 'h1')} h passa a {MED('recuperacao_sem_flaky_h', 'mediana', 'h1')} h: sem efeito prático.", "bad"),
        ]),
    ),
    grid(
        chart("Distribuição do tempo de recuperação", "Mediana por repositório, em escala logarítmica. Os fundos cinza marcam as faixas DORA (1 hora, 1 dia e 1 semana).", "hist", "metricas", preset="rec"),
        chart("Repositórios por faixa de recuperação", "A maior parte volta ao verde em menos de um dia.", "bars", "metricas", preset="rec_classes"),
    ),
    concl(
        [f"Quando o CI quebra, em geral volta ao verde no mesmo dia: mediana de {MED('recuperacao_h', 'mediana', 'h1')} h, e metade dos repositórios entre {MED('recuperacao_h', 'q1', 'h1')} h e {MED('recuperacao_h', 'q3', 'h1')} h.",
         f"O risco está na cauda: {OBS('rq04_repos_acima_1dia', 'int')} repositórios têm mediana acima de um dia e {OBS('rq04_repos_acima_1sem', 'int')} acima de uma semana.",
         f"A censura quase não aparece ({OBS('rq04_pct_eps_censurados', 'pct1')} dos episódios) e a filtragem por flaky quase não muda nada ({OBS('rq04_eps_so_flaky', 'int')} episódios), então essas duas expectativas da hipótese não se sustentam."],
        [f"{OBS('rq04_sem_recuperacao', 'int')} dos {OBS('n_repos', 'int')} repositórios não têm episódio de falha de CI e ficam fora desta métrica.",
         "A recuperação é medida de um workflow, do início da primeira falha até o fim do próximo sucesso, e a mediana do repositório reúne todos os seus workflows.",
         "As hipóteses foram registradas depois da coleta."],
    ),
)

# =====================================================================================================
# RQ 05
# =====================================================================================================
rq05 = page(
    "rq05",
    head("RQ 05 · responsável: C", "Repositórios com maior frequência de deploy apresentam maior ou menor taxa de falha?", "par",
         "vale para o CFR de CI, não para o por release"),
    kpis(
        kpi("ρ com o CFR de CI (a)", V("rq05_spearman", "rho", "s2", "variante=cfr_a"), f"p = {V('rq05_spearman', 'pvalue', 'd2', 'variante=cfr_a')}, não significativo"),
        kpi("ρ com o CFR por release (b)", V("rq05_spearman", "rho", "s2", "variante=cfr_b"), "p &lt; 0,001, significativo"),
        kpi("Repositórios", V("rq05_spearman", "n", "int", "variante=cfr_a"), "em cada correlação"),
    ),
    two(
        hyp(["Seguindo a afirmação do DORA de que velocidade e estabilidade não são um trade-off, esperamos uma correlação de Spearman fraca e negativa entre a frequência de deploys e a taxa de falha.",
             "Esperamos, contudo, que a magnitude seja pequena (<span class='nb'>|ρ| &lt; 0,3</span>), já que a frequência de releases depende também de fatores alheios à qualidade do processo."], prov_ok=False),
        claims([
            ("Correlação fraca e negativa entre frequência e CFR", f"CFR (a): ρ = {V('rq05_spearman', 'rho', 's2', 'variante=cfr_a')}, fraca, negativa e não significativa. CFR (b): ρ = {V('rq05_spearman', 'rho', 's2', 'variante=cfr_b')}, forte e positiva.", "par"),
            ("Magnitude pequena (<span class='nb'>|ρ| &lt; 0,3</span>)", f"Vale para o CFR (a) (|ρ| = {V('rq05_spearman', 'rho', 'abs2', 'variante=cfr_a')}); não vale para o (b) (|ρ| = {V('rq05_spearman', 'rho', 'abs2', 'variante=cfr_b')}).", "par"),
        ]),
    ),
    grid(
        chart("Frequência × CFR de CI (a)", "Cada ponto é um repositório. Sem padrão visível, o que combina com a ausência de correlação.", "scatter", "metricas", y="cfr_a", ylabel="CFR de CI (a)", color="0"),
        chart("Frequência × CFR por release (b)", "Aqui os repositórios mais frequentes aparecem com CFR mais alto.", "scatter", "metricas", y="cfr_b", ylabel="CFR por release (b)", color="1"),
    ),
    concl(
        [f"Com a falha de CI, velocidade e estabilidade não se relacionam de forma detectável (ρ = {V('rq05_spearman', 'rho', 's2', 'variante=cfr_a')}, p = {V('rq05_spearman', 'pvalue', 'd2', 'variante=cfr_a')}, n = {V('rq05_spearman', 'n', 'int', 'variante=cfr_a')}). Não há sinal de trade-off, em linha com o DORA.",
         f"Com a release corretiva, quem publica mais aparece como menos estável (ρ = {V('rq05_spearman', 'rho', 's2', 'variante=cfr_b')}), o contrário do DORA e da hipótese. É provável que isso seja em parte mecânico: quem publica com frequência tem mais chance de ter outra release em até 7 dias, e a heurística lê isso como correção. É uma hipótese, e esta análise não a testa.",
         "A conclusão sobre a RQ 05 depende da definição de CFR."],
        ["Correlação não implica causalidade.",
         "O (b) herda a baixa precisão da heurística da release corretiva (RQ 03).",
         "As hipóteses foram registradas depois da coleta."],
    ),
)

# =====================================================================================================
# RQ 06
# =====================================================================================================
rq06 = page(
    "rq06",
    head("RQ 06 · responsável: A", "Quais características dos repositórios estão associadas a um melhor desempenho DORA?", "par",
         "a idade pesa mais do que se esperava"),
    kpis(
        kpi("Testes feitos", OBS("rq06_n_testes", "int"), "5 fatores × métricas, com Kruskal-Wallis"),
        kpi("Com ε² abaixo de 0,06", OBS("rq06_eps_baixo", "int"), "associações fracas, como previsto"),
        kpi("Significativos após Holm", OBS("rq06_sig_holm", "int"), "p ajustado abaixo de 0,05"),
        kpi("Maior efeito", F6("idade_q", "cfr_b", "epsilon2", "d2"), "ε², idade × CFR por release"),
    ),
    two(
        hyp(["A maior parte das associações será fraca (ε² abaixo de 0,06) e, depois da correção de Holm, poucos testes serão significativos.",
             "Devem se destacar: automação de release, Conventional Commits, número de contribuidores (mais releases) e linguagem (JavaScript/TypeScript e Go acima de C e C++).",
             "Esperamos efeito pequeno ou nulo de popularidade (estrelas) e de idade."]),
        claims([
            ("A maior parte das associações é fraca (ε² &lt; 0,06)", f"{OBS('rq06_eps_baixo', 'int')} dos {OBS('rq06_n_testes', 'int')} testes ficam abaixo de 0,06: cerca de metade.", "par"),
            ("Poucos testes significativos após Holm", f"{OBS('rq06_sig_holm', 'int')} dos {OBS('rq06_n_testes', 'int')} testes.", "par"),
            ("Linguagem: JavaScript/TypeScript e Go acima de C++", f"Frequência mediana de {GR('linguagem', 'TypeScript', 'freq_release', 'd2')} (TypeScript), {GR('linguagem', 'Go', 'freq_release', 'd2')} (Go) e {GR('linguagem', 'JavaScript', 'freq_release', 'd2')} (JavaScript) contra {GR('linguagem', 'C++', 'freq_release', 'd2')} em C++; efeito significativo (ε² {F6('linguagem_top', 'freq_release', 'epsilon2', 'd2')}).", "ok"),
            ("Mais contribuidores, maior frequência de releases", f"Sem associação: ε² de {F6('contribuidores_q', 'freq_release', 'epsilon2', 'd2')}, não significativa.", "bad"),
            ("Popularidade (estrelas): efeito pequeno ou nulo", f"Nenhum dos 5 testes é significativo; ε² de até {F6('estrelas_q', 'freq_release', 'epsilon2', 'd2')}.", "ok"),
            ("Idade: efeito pequeno ou nulo", f"Efeito grande: ε² de {F6('idade_q', 'freq_release', 'epsilon2', 'd2')} (frequência), {F6('idade_q', 'lt_commit_h', 'epsilon2', 'd2')} (lead time) e {F6('idade_q', 'cfr_b', 'epsilon2', 'd2')} (CFR b), todos significativos.", "bad"),
            ("Automação de release e Conventional Commits se destacam", "Não foram testados: a análise usou linguagem, estrelas, contribuidores, idade e tipo do projeto.", "nao"),
        ]),
    ),
    grid(chart("Tamanho de efeito de cada teste", "Cada linha é um fator contra uma métrica. A linha tracejada marca ε² = 0,06, o limite da hipótese; círculos cheios são significativos após Holm.", "dots", "rq06_fatores")),
    grid(
        chart("Frequência por linguagem", "Mediana de releases por semana; só as 7 linguagens mais frequentes têm grupo próprio.", "bars", "rq06_grupos", preset="grupo_freq", fator="linguagem"),
        chart("Frequência por idade do repositório", "Quartis de idade, do mais novo (Q1) ao mais velho (Q4).", "bars", "rq06_grupos", preset="grupo_freq", fator="idade"),
    ),
    concl(
        [f"O fator mais associado ao desempenho é a idade. Repositórios mais novos publicam mais ({GR('idade', 'Q1', 'freq_release', 'd2')} releases por semana no quartil mais novo contra {GR('idade', 'Q4', 'freq_release', 'd2')} no mais velho) e entregam mais rápido, mas têm CFR por release mais alto ({GR('idade', 'Q1', 'cfr_b', 'pct0')} contra {GR('idade', 'Q4', 'cfr_b', 'pct0')}).",
         "A linguagem pesa em frequência, lead time e CFR (b); o número de contribuidores só aparece no lead time (b). A popularidade, medida em estrelas, não faz diferença.",
         f"O tipo do projeto não mostra efeito detectável, mas só foi testado nos {F6('tipo_projeto', 'freq_release', 'n_total', 'int')} repositórios rotulados à mão, com pouco poder estatístico."],
        ["O teste de Kruskal-Wallis diz que há diferença entre grupos, não qual grupo difere; a direção vem das medianas por grupo.",
         "Com 25 testes, sem a correção de Holm haveria falsos positivos; o ε² mede o tamanho do efeito, não a causa.",
         "Automação de release e Conventional Commits existem em repos.csv, mas a análise da RQ 06 não os usa."],
    ),
)

# =====================================================================================================
# RQ 07
# =====================================================================================================
rq07 = page(
    "rq07",
    head("RQ 07 · responsável: A (análise: C)", "O quanto a classificação DORA de um repositório depende da definição operacional escolhida?", "par",
         "depende, e mais do que o previsto"),
    kpis(
        kpi("Mudam de classe em algum par", OBS("rq07_pct_mudou_algum", "pct1"), f"{OBS('rq07_n_mudou_algum', 'int')} de {OBS('n_repos', 'int')} repositórios"),
        kpi("Kappa C1 × C2", PAR("C1xC2", "kappa", "d2"), "concordância " + PAR("C1xC2", "concordancia", "txt")),
        kpi("Kappa C1 × C3", PAR("C1xC3", "kappa", "d2"), "concordância " + PAR("C1xC3", "concordancia", "txt")),
        kpi("Kappa C2 × C3", PAR("C2xC3", "kappa", "d2"), "concordância " + PAR("C2xC3", "concordancia", "txt")),
    ),
    two(
        hyp(["A classificação dependerá de forma relevante da definição escolhida. Esperamos que entre 30% e 50% dos repositórios mudem de categoria em pelo menos um dos pares (C1×C2, C1×C3, C2×C3) e kappa ponderado de concordância moderada, entre 0,3 e 0,6.",
             "A maior parte da mudança deve vir do lead time (a contra b) e da unidade de deploy (release contra tag). Esperamos que o CFR (a contra b) mude a classe com menos frequência."]),
        claims([
            ("30% a 50% mudam de categoria em ao menos um par", f"{OBS('rq07_pct_mudou_algum', 'pct1')} mudam: acima da faixa. Por par: {PAR('C1xC2', 'pct_mudou', 'pct1')}, {PAR('C1xC3', 'pct_mudou', 'pct1')} e {PAR('C2xC3', 'pct_mudou', 'pct1')}.", "par"),
            ("Kappa ponderado entre 0,3 e 0,6, nenhum quase perfeito", f"C1×C2 de {PAR('C1xC2', 'kappa', 'd2')} e C2×C3 de {PAR('C2xC3', 'kappa', 'd2')} cabem na faixa; C1×C3 chega a {PAR('C1xC3', 'kappa', 'd2')}. Nenhum é quase perfeito.", "par"),
            ("A mudança vem do lead time e da unidade de deploy; o CFR pesa menos", f"É o contrário: o CFR muda a nota de {V('rq07_mudanca', 'pct_nota_mudou', 'pct1', 'par=C1xC2&amp;metrica=cfr')} dos repositórios, o lead time de {V('rq07_mudanca', 'pct_nota_mudou', 'pct1', 'par=C1xC2&amp;metrica=lead_time')} e a unidade de deploy de {V('rq07_mudanca', 'pct_nota_mudou', 'pct1', 'par=C1xC2&amp;metrica=freq')} a {V('rq07_mudanca', 'pct_nota_mudou', 'pct1', 'par=C1xC3&amp;metrica=freq')}.", "bad"),
        ]),
    ),
    grid(
        chart("Classe DORA em cada combinação", "A C2 empurra repositórios para baixo; a C3 os empurra para cima.", "cols", "rq07_contagem"),
        chart("Para onde vão os repositórios", "Escolha o par para ver a matriz de transição.", "heat", "rq07_transicoes"),
        chart("Onde a definição pesa", "Maior % de repositórios cuja nota da métrica muda entre dois pares.", "metricchange", "rq07_mudanca"),
    ),
    concl(
        [f"A classificação depende da definição, e quase sempre por causa do CFR. Os pares com o CFR trocado (a por b) concordam pouco (kappa de {PAR('C1xC2', 'kappa', 'd2')} e {PAR('C2xC3', 'kappa', 'd2')}); C1 e C3, que mantêm o mesmo CFR, concordam muito mais ({PAR('C1xC3', 'kappa', 'd2')}).",
         f"Na C2, {PAR('C1xC2', 'desceram', 'int')} repositórios descem de classe e só {PAR('C1xC2', 'subiram', 'int')} sobem, porque o CFR por release é bem mais alto que o de CI.",
         "Por isso as conclusões sobre CFR (RQ 03, 05 e 06) mudam com a definição, enquanto as de frequência e lead time (RQ 01 e 02) sobrevivem na mediana. Para o artigo, vale reportar o CFR (a) e o (b) lado a lado."],
        ["A C3 não é uma definição por tag completa: troca a frequência por tags, mas o lead time (b) continua medido sobre commits entre releases, porque os commits foram coletados por release.",
         "A parte do CFR (b) herda a precisão baixa da heurística; parte da distância da C2 é erro de medida.",
         "São só três combinações, com os cortes fixos da disciplina, e a análise é exploratória."],
    ),
)

# =====================================================================================================
# RQ 08
# =====================================================================================================
rq08 = page(
    "rq08",
    head("RQ 08 (bônus) · 08a: B, 08b: C", "As entregas têm retrabalho, e as métricas de CI melhoraram ou pioraram ao longo da janela?", "par",
         "a 08b tem análise completa; a 08a é exploratória"),
    kpis(
        kpi("08a · Rework rate (mediana)", MED("rework_rate", "mediana", "pct0"), f"contra {MED('cfr_b', 'mediana', 'pct1')} do CFR (b)"),
        kpi("08a · Com rework de 100%", OBS("rq08a_pct_rework_1", "pct1"), f"{OBS('rq08a_n_rework_1', 'int')} repositórios"),
        kpi("08b · Sem tendência no CFR", R8("cfr_a", "pct_sem_tendencia", "pct1"), f"de {R8('cfr_a', 'testados', 'int')} repositórios testados"),
        kpi("08b · Melhora × piora no CFR", f"{R8('cfr_a', 'melhora', 'int')} × {R8('cfr_a', 'piora', 'int')}", "repositórios com tendência significativa"),
    ),
    two(
        hyp(["<b>08a (B).</b> O rework rate (sem limite de dias) será sistematicamente maior que o CFR (b), pois captura correções tardias. Estimamos uma diferença de pelo menos 5 p.p. na mediana.",
             "<b>08b (C).</b> A maioria dos repositórios não terá tendência significativa na taxa de falha de CI nem no tempo de recuperação, e entre os com tendência esperamos mais casos de melhora do que de piora."]),
        claims([
            ("08a · Rework rate maior que o CFR (b), com 5 p.p. a mais na mediana", f"Mediana de {MED('rework_rate', 'mediana', 'pct0')} contra {MED('cfr_b', 'mediana', 'pct1')} ({OBS('rq08a_dif_pp', 'pp1')} de diferença); o rework é maior em {OBS('rq08a_pct_maior_cfr_b', 'pct1')} dos repositórios.", "ok"),
            ("08b · A maioria sem tendência significativa", f"{R8('cfr_a', 'pct_sem_tendencia', 'pct1')} no CFR de CI e {R8('recuperacao_h', 'pct_sem_tendencia', 'pct1')} na recuperação.", "ok"),
            ("08b · Entre os com tendência, mais melhora do que piora", f"CFR: {R8('cfr_a', 'melhora', 'int')} melhoras e {R8('cfr_a', 'piora', 'int')} pioras; recuperação: {R8('recuperacao_h', 'melhora', 'int')} e {R8('recuperacao_h', 'piora', 'int')}. Após Holm: {R8('cfr_a', 'melhora_holm', 'int')} melhoras e {R8('cfr_a', 'piora_holm', 'int')} piora no CFR. Numericamente sim, sem sustentação estatística.", "par"),
        ]),
    ),
    grid(
        chart("08a · Distribuição do rework rate", "Metade dos repositórios tem todas as releases avaliadas como corretivas.", "hist", "metricas", preset="rework"),
        chart("08a · Rework rate contra o CFR (b)", "Com limite de 7 dias o rework coincide com o CFR (b).", "bars", "medianas", preset="rq08a"),
    ),
    grid(
        chart("08b · Direção das tendências por repositório", "Mann-Kendall mensal, α = 0,05. Em baixo de cada métrica, o resultado com correção de Holm.", "seg", "rq08b_resumo"),
        chart("08b · CFR de CI ao longo dos 12 meses", "Mediana mensal entre repositórios. O Mann-Kendall da mediana não acusa tendência.", "lineband", "rq08b_serie", metric="cfr_a", scale="100", unit="%"),
        chart("08b · Tempo de recuperação ao longo dos 12 meses", "Mediana mensal entre os repositórios com episódios no mês.", "lineband", "rq08b_serie", metric="recuperacao_h", scale="1", unit=" h"),
    ),
    grid(
        chart("08b · Frequência de releases por trimestre", "Só descritivo. O primeiro trimestre pode refletir sazonalidade de fim de ano.", "bars", "rq08b_freq_tri", preset="rq08b_freq"),
        chart("08b · Lead time por trimestre", "Só descritivo, sem teste.", "bars", "rq08b_lt_tri", preset="rq08b_lt"),
    ),
    concl(
        [f"<b>08a.</b> A diferença prevista aparece ({OBS('rq08a_dif_pp', 'pp1')}), mas o rework rate sem limite de dias satura: {OBS('rq08a_pct_rework_1', 'pct1')} dos repositórios têm 100% das releases classificadas como corretivas, e a métrica deixa de discriminar. Com janela de 7 dias, ela coincide com o CFR (b). A correlação entre rework e CFR (b) é de {OBS('rq08a_rho_cfr_b', 's2')}.",
         f"<b>08b.</b> A maioria dos repositórios não muda ao longo da janela ({R8('cfr_a', 'pct_sem_tendencia', 'pct1')} no CFR e {R8('recuperacao_h', 'pct_sem_tendencia', 'pct1')} na recuperação). A expectativa de mais melhora do que piora não se sustenta: o CFR tem {R8('cfr_a', 'melhora', 'int')} melhoras e {R8('cfr_a', 'piora', 'int')} pioras, e com a correção de Holm sobra só uma piora.",
         f"A série mensal da mediana também não tem tendência (p = {V('rq08b_mk', 'p', 'd2', 'metrica=cfr_a')} no CFR e {V('rq08b_mk', 'p', 'd2', 'metrica=recuperacao_h')} na recuperação)."],
        [f"A 08a é uma análise exploratória feita para este painel: não está em analise/ do repositório, porque a Issue #77 escolheu a 08b.",
         f"A recuperação só cobre {R8('recuperacao_h', 'testados', 'int')} repositórios: {R8('recuperacao_h', 'excluidos', 'int')} não têm 8 meses com episódio de falha e ficam fora do teste.",
         "Com 12 pontos por série, o teste tem pouco poder: sem tendência quer dizer não detectável, e não estável.",
         "A hipótese da 08b foi registrada depois da coleta."],
    ),
)

TABS = [("geral", "Visão geral", "Resumo", None), ("rq01", "RQ 01", "Frequência", "ok"), ("rq02", "RQ 02", "Lead time", "par"),
        ("rq03", "RQ 03", "Taxa de falha", "bad"), ("rq04", "RQ 04", "Recuperação", "par"), ("rq05", "RQ 05", "Velocidade × falha", "par"),
        ("rq06", "RQ 06", "Fatores", "par"), ("rq07", "RQ 07", "Sensibilidade", "par"), ("rq08", "RQ 08", "Bônus", "par")]
DOT = {"ok": "var(--color-ok)", "par": "var(--color-warn)", "bad": "var(--color-bad)"}


def tab_btn(i, a, b, k):
    d = f'<span class="px-dot" style="background:{DOT[k]}"></span>' if k else ""
    return f'<button type="button" class="px-tab" role="tab" data-tab="{i}" aria-selected="false"><b>{d}{a}</b><small>{b}</small></button>'


PAGINAS = geral + rq01 + rq02 + rq03 + rq04 + rq05 + rq06 + rq07 + rq08


def navegacao() -> str:
    return "".join(tab_btn(t[0], t[1], t[2], t[3]) for t in TABS)


def titulo_html() -> str:
    return f"Métricas DORA em {OBS('n_repos', 'int')} repositórios open-source"
