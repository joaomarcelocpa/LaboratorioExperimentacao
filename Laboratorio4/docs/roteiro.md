# Roteiro de apresentação — 15 perguntas

Respostas curtas (~30 s cada). As perguntas são divididas: cada integrante responde às perguntas marcadas com seu nome.

---

## João (perguntas 1, 3, 8, 14, 15)

**1. Qual é o cenário de vocês e o que H₀ e H₁ afirmam, em palavras simples?**
Comparamos o tempo até o merge de PRs de agentes de IA que tiveram revisão de bot com os que tiveram revisão só humana. H₀ diz que o bot não faz diferença no tempo; H₁ diz que faz — em qualquer direção.

**3. Como os dados reais foram coletados, e o que eles mostraram sobre a forma da distribuição?**
Baixamos o dataset AIDev (Hugging Face) e filtramos 60 PRs do agente Claude Code: 30 com bot e 30 sem bot, sorteados com semente fixa. Os dados são muito assimétricos — a maioria dos PRs demora poucas horas, mas alguns levam centenas, puxando a média para cima. A forma lembra claramente uma lognormal.

**8. No cenário de vocês, o que seria um erro tipo I e um erro tipo II? Qual dos dois seria mais grave?**
Erro tipo I: concluir que o bot altera o tempo de merge quando na verdade não altera — seria uma recomendação falsa. Erro tipo II: não detectar uma diferença real — perderíamos uma oportunidade de otimizar o processo. No nosso contexto, o erro tipo I é mais grave porque pode levar a mudanças desnecessárias de processo.

**14. Nos dados reais, os dois testes chegaram à mesma conclusão? O tamanho do efeito tem importância prática?**
Sim, os dois não rejeitaram H₀. Mas o efeito não é pequeno: a mediana sem bot é ~2,5 vezes maior. O problema é o poder — com n=30 e dados tão assimétricos, a amostra é pequena demais para detectar a diferença com confiança estatística.

**15. Qual teste vocês recomendam para o cenário, em que situação mudariam a recomendação, e qual é a principal limitação do estudo?**
Recomendamos o Mann-Whitney: ele controlou melhor o α e teve muito mais poder nos dados lognormais. Mudaríamos para o Welch se os dados fossem aproximadamente normais ou se n fosse grande o suficiente (≥100) para o TLC estabilizar a média. A principal limitação é que todos os PRs são de agentes de IA — o resultado pode não valer para PRs humanos.

---

## Miguel (perguntas 5, 6, 7, 11, 12)

**5. O que cada um dos dois testes compara de fato (médias, postos, proporções...)?**
O t de Welch compara as **médias** dos dois grupos. O Mann-Whitney compara os **postos** (ranks) — a ideia é: se sortearmos um PR de cada grupo, qual tem maior chance de ter demorado mais? Não assume nenhuma distribuição, só a ordem dos valores.

**6. No G2: o que é a distribuição da estatística sob H₀, e por que a região de rejeição fica onde fica?**
Sob H₀, a estatística t segue aproximadamente uma distribuição t de Student com graus de liberdade calculados pelo método de Welch (≈29 no exemplo do G2). A região de rejeição fica nas duas caudas porque o teste é bicaudal: valores de t muito positivos ou muito negativos são igualmente evidência contra H₀.

**7. O que significa o p-valor do exemplo mostrado no G2? E o que ele não significa?**
O p-valor é a probabilidade de obter uma estatística tão extrema quanto a observada (ou mais) se H₀ fosse verdadeira. No exemplo, p = 0,184 significa que há 18,4% de chance de ver esse t só por acaso sob H₀. O p-valor **não** é a probabilidade de H₀ ser verdadeira, nem a probabilidade de erro.

**11. Que violação de pressuposto vocês simularam, e por que ela afeta mais um teste do que o outro?**
Simulamos dados mais assimétricos (σ_log maior) e amostras pequenas (n pequeno). O Welch assume que a média amostral é aproximadamente normal — o que falha com dados assimétricos e n pequeno — ficando ainda mais conservador. O Mann-Whitney não assume normalidade, então é afetado bem menos.

**12. Se vocês usassem α = 0,01 em vez de 0,05, o que mudaria no G3 e no G4?**
No G3, a linha de referência desceria de 5% para 1%. O Welch, que já estava em 1,4%, ficaria bem perto da linha — ou até a cruzaria — e o MW cairia de 4,7% para algo bem abaixo de 1%, ficando conservador também. No G4, as curvas de poder cairiam para todos os efeitos, porque o limiar para rejeição fica mais exigente.

---

## Bernardo (perguntas 2, 4, 9, 10, 13)

**2. O teste de vocês é unicaudal ou bicaudal? Por quê?**
Bicaudal. Não temos razão prévia para apostar em uma direção: o bot pode acelerar o merge (feedback automatizado chega mais rápido) ou atrasar (mais rodadas de revisão antes do merge). Como queremos detectar diferença em qualquer sentido, a hipótese alternativa é bilateral.

**4. Como os dados reais ajudaram a escolher os parâmetros da simulação?**
Calculamos a média e o desvio-padrão do logaritmo natural das horas reais para cada grupo. Esses dois números (μ_log e σ_log) são exatamente os parâmetros da lognormal do NumPy. Assim a simulação reproduz a assimetria, a mediana e a dispersão observadas: com_bot com μ=1,616 e σ=2,374; sem_bot com μ=2,638 e σ=2,671.

**9. No G3, algum teste se afastou de 5%? Ele ficou liberal ou conservador, e por quê?**
O Welch ficou muito **conservador**: 1,4% de erro tipo I em vez dos 5% esperados. Com dados lognormais, a variância da média amostral é enorme — a estatística t raramente atinge o valor crítico mesmo quando H₀ é verdadeira. O Mann-Whitney ficou próximo do esperado (4,7%), pois compara postos e é robusto à assimetria.

**10. No G4, qual teste tem mais poder? A diferença entre eles muda conforme o tamanho do efeito?**
O Mann-Whitney tem muito mais poder em todos os tamanhos de efeito. Com razão de medianas = 2, o MW chega a 16,5% contra 3,3% do Welch. Com razão = 5, o MW atinge 65% contra 13% do Welch. A diferença **aumenta** com o efeito: o Welch começa já defasado por ser conservador, e essa desvantagem se acumula.

**13. A simulação confirmou o que o grupo esperava antes de simular? Se não, o que explica a diferença?**
Sim, confirmou exatamente. O grupo esperava que o Mann-Whitney se saísse melhor com dados assimétricos e amostras pequenas, e foi o que aconteceu: o Welch ficou conservador (1,4% de erro tipo I) e com poder muito inferior. A intuição de que a média é instável com dados lognormais e outliers se mostrou correta na simulação.
