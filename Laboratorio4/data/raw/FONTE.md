# Fonte dos dados reais

**Arquivo:** `prs.csv` (60 PRs: 30 `com_bot` e 30 `sem_bot`)

## Origem
Dataset **AIDev** (Hugging Face, licença CC-BY-4.0): <https://huggingface.co/datasets/hao-li/AIDev>.
Tabelas usadas: `pull_request.parquet` (datas de abertura e merge) e `pr_reviews.parquet` (quem revisou, com `user_type`).

## Como foi coletado
Script `src/coletar_dados.py`, com semente fixa 42:

1. Só PRs escritos pelo agente `Claude_Code` e **mesclados** (`merged_at` preenchido). Um único agente reduz a diferença entre os grupos.
2. Variável medida: `horas_ate_merge` = `merged_at` - `created_at`, em horas.
3. Só contam revisões enviadas **antes** do merge.
4. **`com_bot`:** o PR recebeu revisão de ao menos um destes bots: `copilot-pull-request-reviewer`, `coderabbitai`, `gemini-code-assist`, `greptile-apps`, `cubic-dev-ai`.
5. **`sem_bot`:** o PR recebeu revisão de pessoas (`user_type == User`) e de nenhum bot acima.
6. PRs sem nenhuma revisão foram descartados.
7. Amostra aleatória de 30 PRs por grupo.

## Limitações
- Todos os PRs são de agentes de IA em repositórios com mais de 100 estrelas, então os resultados não valem para PRs escritos por pessoas.
- Os PRs vêm de repositórios diferentes (29 em cada grupo), e a cultura de cada projeto pode influenciar o tempo de merge.
- "Sem bot" significa "revisão só humana". PRs sem revisão ficaram de fora.
- Amostra pequena (30 por grupo), conforme a especificação.
