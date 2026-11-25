package labexp.aceitacao.p8;

import static com.microsoft.playwright.assertions.PlaywrightAssertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertEquals;

import com.fasterxml.jackson.databind.JsonNode;
import com.microsoft.playwright.Browser;
import com.microsoft.playwright.Page;
import com.microsoft.playwright.Playwright;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Callable;
import labexp.aceitacao.ApiClient.Resposta;
import labexp.aceitacao.Base;
import labexp.aceitacao.Json;
import org.junit.jupiter.api.Test;

/** P8: relatorio agregado. Fronteira: HTTP (GET /relatorio/tarefas); a tela de tarefas por data-testid. */
class P8RelatorioTest extends Base {

    private static final String[] PENDENTES = {"pendentes", "pendente", "pending"};
    private static final String[] CONCLUIDAS = {"concluidas", "concluida", "completed", "done"};
    private static final String[] VENCIDAS = {"vencidas", "vencida", "atrasadas", "overdue"};

    /** Cria n tarefas em paralelo; devolve os ids. */
    private List<String> criar(int n, String responsavel, String vencimento) {
        List<Callable<String>> cargas = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            String titulo = tituloUnico("rel");
            cargas.add(() -> {
                Resposta r = api.criar(titulo, responsavel, vencimento);
                assertEquals(201, r.status(), r.corpo());
                return r.id();
            });
        }
        return emParalelo(cargas);
    }

    private void concluir(List<String> ids) {
        List<Callable<Integer>> cargas = new ArrayList<>();
        for (String id : ids) {
            cargas.add(() -> api.concluir(id).status());
        }
        emParalelo(cargas).forEach(s -> assertEquals(200, s));
    }

    private JsonNode relatorio() {
        Resposta r = api.get("/relatorio/tarefas");
        assertEquals(200, r.status(), r.corpo());
        return r.json();
    }

    @Test
    void relatorioBateComEstadoInserido() {
        esvaziarBase();
        String resp = responsavelUnico();
        // 5 pendentes (2 delas vencidas) e 3 concluidas; as concluidas tambem tem prazo vencido
        // para provar que tarefa concluida nao conta como vencida.
        criar(3, resp, FUTURO);
        criar(2, resp, PASSADO);
        concluir(criar(3, resp, PASSADO));

        JsonNode r = relatorio();
        assertEquals(5L, Json.contador(r, PENDENTES).orElseThrow(() -> new AssertionError("sem contador de pendentes: " + r)));
        assertEquals(3L, Json.contador(r, CONCLUIDAS).orElseThrow(() -> new AssertionError("sem contador de concluidas: " + r)));
        assertEquals(2L, Json.contador(r, VENCIDAS).orElseThrow(() -> new AssertionError("sem contador de vencidas: " + r)));
    }

    @Test
    void distribuicaoPorResponsavelCorreta() {
        String ana = responsavelUnico();
        String bia = responsavelUnico();
        criar(2, ana, FUTURO);
        criar(1, ana, PASSADO);
        concluir(criar(1, ana, FUTURO));
        criar(1, bia, FUTURO);
        concluir(criar(1, bia, FUTURO));

        JsonNode r = relatorio();
        assertEquals(4L, Json.totalDoResponsavel(r, ana).orElseThrow(() -> new AssertionError("responsavel ausente: " + r)),
                "soma de todas as tarefas, independente do status");
        assertEquals(2L, Json.totalDoResponsavel(r, bia).orElseThrow(() -> new AssertionError("responsavel ausente: " + r)));
    }

    @Test
    void telaDeListagemContinuaFuncionando() {
        String resp = responsavelUnico();
        String titulo = tituloUnico("lista");
        String id = api.criar(titulo, resp, FUTURO).id();

        // a API de tarefas segue igual
        assertEquals(200, api.consultar(id).status());
        assertEquals(1, Json.itens(api.listar().json()).stream()
                .filter(t -> t.get("id").asText().equals(id)).count());

        // e a tela de tarefas segue mostrando a lista e o formulario
        try (Playwright playwright = Playwright.create(); Browser browser = playwright.chromium().launch()) {
            Page page = browser.newPage();
            page.navigate(BASE_URL);
            assertThat(page.getByTestId("lista-tarefas")).isVisible();
            assertThat(page.getByTestId("tarefa-item").filter(new com.microsoft.playwright.Locator.FilterOptions()
                    .setHasText(resp))).hasCount(1);
            assertThat(page.getByTestId("tarefa-titulo").filter(new com.microsoft.playwright.Locator.FilterOptions()
                    .setHasText(titulo))).hasCount(1);
        }
    }

    @Test
    void relatorioBaseVaziaRetornaZeros() {
        esvaziarBase();

        JsonNode r = relatorio();
        assertEquals(0L, Json.contador(r, PENDENTES).orElseThrow(() -> new AssertionError("sem contador de pendentes: " + r)));
        assertEquals(0L, Json.contador(r, CONCLUIDAS).orElseThrow(() -> new AssertionError("sem contador de concluidas: " + r)));
        assertEquals(0L, Json.contador(r, VENCIDAS).orElseThrow(() -> new AssertionError("sem contador de vencidas: " + r)));
    }
}
