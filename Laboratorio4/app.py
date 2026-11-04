"""Dashboard do Lab 04: t de Welch x Mann-Whitney no tempo até o merge de PRs.

Uso: streamlit run app.py
"""

from pathlib import Path

import streamlit as st

RAIZ = Path(__file__).parent
FIGURAS = RAIZ / "results" / "figures"

LINK_REPOSITORIO = "https://github.com/joaomarcelocpa/LaboratorioExperimentacao"
LINK_PROJECTS = "https://github.com/users/joaomarcelocpa/projects/2"

st.set_page_config(page_title="Lab 04: testes de hipótese por dentro", layout="wide")


def em_construcao(sprint: str) -> None:
    st.info(f"Esta seção será preenchida na {sprint}.")


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
em_construcao("Sprint 2 (gráfico G3)")

st.header("5. Poder")
em_construcao("Sprint 2 (gráfico G4)")

st.header("6. Dados reais")
em_construcao("entrega final (tabela com estatística, p-valor, tamanho do efeito e conclusão)")

st.header("7. Conclusão")
em_construcao("entrega final")
