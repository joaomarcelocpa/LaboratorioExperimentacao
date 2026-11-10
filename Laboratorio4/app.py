"""Dashboard do Lab 04: t de Welch x Mann-Whitney no tempo até o merge de PRs.

Uso: streamlit run app.py
"""

from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from src.testes import ALFA, aplicar_testes

RAIZ = Path(__file__).parent
FIGURAS = RAIZ / "results" / "figures"

LINK_REPOSITORIO = "https://github.com/joaomarcelocpa/LaboratorioExperimentacao"
LINK_PROJECTS = "https://github.com/users/joaomarcelocpa/projects/2"

st.set_page_config(page_title="Lab 04: testes de hipótese por dentro", layout="wide")


def em_construcao(sprint: str) -> None:
    st.info(f"Esta seção será preenchida na {sprint}.")


def mostrar_grafico(padrao: str, legenda: str, nome: str) -> None:
    """Mostra a figura que casa com o padrão em results/figures, ou avisa que ainda não existe."""
    figuras = sorted(FIGURAS.glob(padrao))
    if figuras:
        st.image(str(figuras[0]), caption=legenda)
    else:
        st.info(f"O {nome} aparece aqui assim que a figura for salva em results/figures/ ({padrao}).")


st.title("Lab 04: testes de hipótese por dentro")
st.caption("t de Welch × Mann-Whitney aplicados ao tempo até o merge de PRs")
st.markdown(
    f"**Repositório:** [{LINK_REPOSITORIO}]({LINK_REPOSITORIO}) · "
    f"**GitHub Projects:** [{LINK_PROJECTS}]({LINK_PROJECTS})"
)

st.header("1. Cenário")
st.markdown(
    "**Pergunta.** PRs de agentes de IA que recebem revisão de bot demoram um tempo "
    "diferente até o merge do que PRs revisados só por humanos?"
)
col_h0, col_h1 = st.columns(2)
col_h0.markdown(
    "**H₀.** As distribuições do tempo até o merge dos grupos `com_bot` e `sem_bot` "
    "são iguais: o bot de revisão não altera o tempo."
)
col_h1.markdown(
    "**H₁.** As distribuições diferem entre os grupos. O teste é bicaudal, porque o bot "
    "pode tanto acelerar quanto atrasar o merge."
)
st.markdown(
    "Os dados reais vêm do dataset público AIDev (Hugging Face), que reúne PRs do GitHub "
    "escritos por agentes de IA. Coletamos **60 PRs mesclados do agente Claude Code**, "
    "sendo 30 revisados por pelo menos um bot de revisão e 30 revisados só por pessoas, "
    "sorteados com semente fixa. A origem e as limitações estão em `data/raw/FONTE.md`."
)

st.header("2. Os dados")
st.image(
    str(FIGURAS / "g1_dados_reais_vs_simulados.png"),
    caption="G1: histogramas do tempo até o merge, dados reais e simulados.",
)
st.markdown(
    "Os tempos reais são muito assimétricos: a mediana é de 7,3 h com bot e 17,8 h sem bot, "
    "mas alguns PRs levam centenas de horas e puxam a média para 44 h e 132 h. "
    "Por isso a simulação usa uma distribuição lognormal em cada grupo, com os parâmetros "
    "(média e desvio-padrão do log das horas) calculados dos dados reais. "
    "Os histogramas estão em escala logarítmica para a cauda longa não esmagar o gráfico, "
    "e o simulado reproduz a assimetria do real."
)

st.header("3. Como os testes funcionam")
st.image(
    str(FIGURAS / "g2_regiao_rejeicao.png"),
    caption="G2: distribuição do t de Welch sob H₀, região de rejeição e p-valor.",
)
st.markdown(
    "O t de Welch compara as **médias** dos dois grupos, e o Mann-Whitney compara os "
    "**postos** (a ordem dos valores). A curva mostra como a estatística t se distribui "
    "quando H₀ é verdadeira. A região de rejeição (em vermelho) são as duas caudas que "
    "somam 5%, a partir de |t| ≥ 2,05. No conjunto simulado de exemplo o t observado foi "
    "−1,36, e o p-valor de 0,184 é a área hachurada: a probabilidade de obter um t tão "
    "extremo quanto esse ou mais, se H₀ fosse verdadeira. Ele não é a probabilidade de H₀ "
    "ser verdadeira."
)

st.header("4. Erro tipo I")
mostrar_grafico("g3*.png", "G3: erro tipo I dos dois testes em cada situação simulada.", "G3")
st.markdown(
    "Com dados lognormais e σ_log ≈ 2,5, o t de Welch ficou **muito conservador**: em 10.000 "
    "simulações sem efeito, rejeitou H₀ apenas 1,4% das vezes — bem abaixo do α = 5% esperado. "
    "Isso acontece porque a variância da média amostral cresce muito com a cauda longa da lognormal, "
    "tornando a estatística t raramente extrema o suficiente para rejeitar. "
    "O Mann-Whitney ficou próximo do esperado (4,7%), pois compara postos em vez de médias e é "
    "naturalmente robusto à assimetria. O gráfico também exibe o comportamento nas situações com "
    "pressupostos violados (Q3), onde essa diferença tende a se acentuar."
)

st.header("5. Poder")
mostrar_grafico("g4*.png", "G4: curvas de poder dos dois testes.", "G4")
st.markdown(
    "O Mann-Whitney detecta o efeito com muito mais poder em todos os tamanhos de efeito simulados. "
    "Com razão de medianas = 2 (próxima da observada nos dados reais), o MW chega a 16,5% de poder "
    "contra apenas 3,3% do Welch; com razão = 5, o MW atinge 65% enquanto o Welch fica em 13%. "
    "A diferença aumenta conforme o efeito cresce porque o Welch começa já defasado — ele perde "
    "poder justamente por ser conservador sob lognormal. A vantagem do MW se mantém (ou cresce) "
    "nas situações de Q3; apenas com dados próximos da normal o Welch poderia competir."
)


@st.cache_data
def testar_dados_reais() -> dict:
    dados = pd.read_csv(RAIZ / "data" / "raw" / "prs.csv")
    horas = dados.groupby("grupo").horas_ate_merge
    com_bot, sem_bot = (horas.get_group(g).to_numpy() for g in ("com_bot", "sem_bot"))
    return {
        "resultado": aplicar_testes(com_bot, sem_bot),
        "mediana_com_bot": float(np.median(com_bot)),
        "mediana_sem_bot": float(np.median(sem_bot)),
        "n": (len(com_bot), len(sem_bot)),
    }


def decisao(p: float) -> str:
    return "rejeita H₀" if p < ALFA else "não rejeita H₀"


st.header("6. Dados reais")
real = testar_dados_reais()
r = real["resultado"]
welch, mw = r["welch"], r["mann_whitney"]
tabela = pd.DataFrame(
    [
        {
            "Teste": "t de Welch",
            "Estatística": f"t = {welch['t']:.2f} (gl = {welch['gl']:.1f})",
            "p-valor": f"{welch['p']:.3f}",
            "Tamanho do efeito": f"d de Cohen = {r['d_cohen']:.2f} (horas); {r['d_cohen_log']:.2f} (log das horas)",
            "Conclusão": f"{decisao(welch['p'])} (α = {ALFA})",
        },
        {
            "Teste": "Mann-Whitney",
            "Estatística": f"U = {mw['U']:.1f}",
            "p-valor": f"{mw['p']:.3f}",
            "Tamanho do efeito": f"P(com bot > sem bot) = {r['prob_superioridade']:.2f}",
            "Conclusão": f"{decisao(mw['p'])} (α = {ALFA})",
        },
    ]
)
st.table(tabela.set_index("Teste"))
razao = real["mediana_sem_bot"] / real["mediana_com_bot"]
concordam = "Os dois testes chegaram à mesma conclusão" if r["concordam"] else "Os dois testes discordam"
st.markdown(
    f"{concordam} (testes bicaudais, α = {ALFA}) nos {real['n'][0]} + {real['n'][1]} PRs reais. "
    f"A mediana do tempo até o merge é de {real['mediana_com_bot']:.1f} h com bot e "
    f"{real['mediana_sem_bot']:.1f} h sem bot, ou seja, PRs sem bot demoram cerca de "
    f"{razao:.1f} vezes mais. O efeito é de tamanho pequeno a médio e relevante na prática "
    "(horas contra dias para mesclar), mas com 30 PRs por grupo e dados tão assimétricos a amostra "
    "é pequena para afirmar a diferença: não rejeitar H₀ aqui não prova que o bot não faz "
    "diferença, só que esta amostra não bastou para detectá-la."
)

st.header("7. Conclusão")
st.markdown(
    "**Palpite vs. resultado.** Antes de simular, o grupo esperava que o Mann-Whitney se saísse "
    "melhor, pois com dados lognormais cheios de outliers a média (que o Welch compara) é instável. "
    "A simulação confirmou: o Welch ficou conservador demais (erro tipo I de 1,4% em vez de 5%), "
    "enquanto o Mann-Whitney manteve o controle sobre α e apresentou poder muito superior em todos "
    "os tamanhos de efeito. Não houve surpresa — o resultado foi exatamente o esperado."
)
st.markdown(
    "**Recomendação.** Para o cenário de tempo até o merge de PRs com dados assimétricos e "
    "amostras pequenas (n ≈ 30), **use o Mann-Whitney**. Ele controla melhor o erro tipo I e "
    "detecta o efeito com mais poder quando os dados são lognormais ou têm outliers."
)
st.markdown(
    "**Quando mudar a escolha.** Use o t de Welch se: (1) os dados forem aproximadamente normais "
    "(por exemplo, após transformação log bem-sucedida); (2) a amostra for grande o suficiente "
    "para o TLC estabilizar a média (n ≥ 100 por grupo, dependendo da assimetria); ou (3) "
    "a comparação de médias tiver interpretação direta e relevante para o problema. "
    "A principal limitação deste estudo é a amostra pequena (30 por grupo) e o fato de todos "
    "os PRs serem de agentes de IA — os resultados podem não se generalizar para PRs humanos."
)
