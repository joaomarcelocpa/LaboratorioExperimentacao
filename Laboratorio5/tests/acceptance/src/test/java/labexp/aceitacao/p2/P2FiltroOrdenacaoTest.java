package labexp.aceitacao.p2;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.fasterxml.jackson.databind.JsonNode;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import labexp.aceitacao.ApiClient;
import labexp.aceitacao.ApiClient.Resposta;
import labexp.aceitacao.Base;
import labexp.aceitacao.Json;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/**
 * P2: filtro e ordenacao com grande volume (50.000 tarefas; P2_VOLUME reduz so para teste do teste).
 *
 * <p>O pedido nao fixa os nomes dos parametros HTTP nem controles de interface. Os testes assumem os nomes
 * naturais da propria API da semente: {@code responsavel} e {@code status} (PENDENTE|CONCLUIDA) em
 * {@code GET /tarefas}, e enviam a ordenacao por varios apelidos ao mesmo tempo (ordenar, ordem, ordenarPor,
 * sort, orderBy = vencimento). Isso e um apontamento para o texto do pedido (minimo observavel).
 */
class P2FiltroOrdenacaoTest {

    private static final int VOLUME = Integer.parseInt(System.getenv().getOrDefault("P2_VOLUME", "50000"));
    private static final int RESPONSAVEIS = 50;
    private static final ApiClient API = ApiClient.comPapel(Base.BASE_URL, "gestor");
    private static final String PREFIXO = "p2-" + UUID.randomUUID().toString().substring(0, 8);
    private static final Instant BASE = Instant.parse("2098-01-01T00:00:00Z");
    private static final String ORDENAR = "ordenar=vencimento&ordem=vencimento&ordenarPor=vencimento"
            + "&sort=vencimento&orderBy=vencimento";

    private static final List<String> ids = Collections.synchronizedList(new ArrayList<>());
    private static String alvo;
    private static int pendentesDoAlvo;
    private static final int CONCLUIDAS_DO_ALVO = 10;

    @BeforeAll
    static void carregar() throws Exception {
        alvo = PREFIXO + "-r0";
        ExecutorService pool = Executors.newFixedThreadPool(16);
        List<Callable<Void>> tarefas = new ArrayList<>();
        for (int i = 0; i < VOLUME; i++) {
            final int n = i;
            tarefas.add(() -> {
                String resp = PREFIXO + "-r" + (n % RESPONSAVEIS);
                String venc = BASE.plusSeconds(n * 420L).toString();
                Resposta r = API.criar("t-" + n, resp, venc);
                assertEquals(201, r.status(), r.corpo());
                ids.add(r.id());
                if (n % RESPONSAVEIS == 0 && n / RESPONSAVEIS < CONCLUIDAS_DO_ALVO) {
                    assertEquals(200, API.concluir(r.id()).status());
                }
                return null;
            });
        }
        pool.invokeAll(tarefas).forEach(f -> {
            try {
                f.get();
            } catch (Exception e) {
                throw new IllegalStateException(e);
            }
        });
        pool.shutdown();
        pendentesDoAlvo = VOLUME / RESPONSAVEIS - CONCLUIDAS_DO_ALVO;
    }

    @AfterAll
    static void limpar() throws Exception {
        ExecutorService pool = Executors.newFixedThreadPool(16);
        List<Callable<Integer>> exclusoes = new ArrayList<>();
        for (String id : ids) {
            exclusoes.add(() -> API.excluir(id).status());
        }
        pool.invokeAll(exclusoes);
        pool.shutdown();
    }

    private Resposta filtrar(String status, String responsavel, boolean ordenado) {
        StringBuilder q = new StringBuilder();
        if (status != null) {
            q.append("status=").append(status).append('&');
        }
        if (responsavel != null) {
            q.append("responsavel=").append(responsavel).append('&');
        }
        if (ordenado) {
            q.append(ORDENAR);
        }
        return API.get("/tarefas?" + q);
    }

    /** Quantos resultados o usuario consegue alcancar: a lista inteira, ou o total declarado numa resposta paginada. */
    private long alcancaveis(Resposta r) {
        JsonNode raiz = r.json();
        long itens = Json.itens(raiz).size();
        if (raiz.isObject()) {
            var total = Json.campo(raiz, "total", "totalElements", "totalItens", "count");
            if (total.isPresent() && total.get().isIntegralNumber()) {
                return Math.max(itens, total.get().asLong());
            }
        }
        return itens;
    }

    @Test
    void filtroRespondeDentroDoTempoComGrandeVolume() {
        filtrar("PENDENTE", alvo, false); // aquecimento: primeira chamada paga JIT e conexao
        long[] tempos = new long[3];
        for (int i = 0; i < tempos.length; i++) {
            Resposta r = filtrar("PENDENTE", alvo, false);
            assertEquals(200, r.status(), r.corpo());
            tempos[i] = r.milissegundos();
        }
        Arrays.sort(tempos);
        assertTrue(tempos[1] <= 1000, "mediana de " + tempos[1] + " ms com " + VOLUME + " tarefas (limite 1000 ms)");
    }

    @Test
    void filtroRetornaTodosOsResultados() {
        Resposta pendentes = filtrar("PENDENTE", alvo, false);
        assertEquals(pendentesDoAlvo, alcancaveis(pendentes));
        for (JsonNode t : Json.itens(pendentes.json())) {
            assertEquals(alvo, t.get("responsavel").asText());
            assertEquals("PENDENTE", t.get("status").asText());
        }
        Resposta concluidas = filtrar("CONCLUIDA", alvo, false);
        assertEquals(CONCLUIDAS_DO_ALVO, alcancaveis(concluidas));
        assertFalse(Json.itens(concluidas.json()).stream().anyMatch(t -> !t.get("status").asText().equals("CONCLUIDA")));
    }

    @Test
    void ordenacaoPorVencimentoCorretaNosExtremos() {
        // entre as pendentes do alvo: a mais proxima e a de indice 500 (as 10 primeiras foram concluidas)
        Resposta r = filtrar("PENDENTE", alvo, true);
        List<JsonNode> itens = Json.itens(r.json());
        assertEquals(pendentesDoAlvo, itens.size());
        assertEquals("t-" + CONCLUIDAS_DO_ALVO * RESPONSAVEIS, itens.get(0).get("titulo").asText(), "primeiro = vencimento mais proximo");
        int ultimo = (VOLUME / RESPONSAVEIS - 1) * RESPONSAVEIS;
        assertEquals("t-" + ultimo, itens.get(itens.size() - 1).get("titulo").asText(), "ultimo = vencimento mais distante");

        // e na lista inteira: nao decrescente, primeiro e o minimo, ultimo e o maximo
        List<JsonNode> todas = Json.itens(filtrar(null, null, true).json());
        Instant anterior = Instant.MIN;
        for (JsonNode t : todas) {
            Instant v = Instant.parse(t.get("vencimento").asText());
            assertFalse(v.isBefore(anterior), "lista fora de ordem em " + t.get("titulo").asText());
            anterior = v;
        }
    }
}
