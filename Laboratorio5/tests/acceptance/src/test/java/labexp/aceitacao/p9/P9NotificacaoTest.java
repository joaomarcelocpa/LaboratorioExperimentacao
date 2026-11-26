package labexp.aceitacao.p9;

import static com.microsoft.playwright.assertions.PlaywrightAssertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.microsoft.playwright.Browser;
import com.microsoft.playwright.Locator;
import com.microsoft.playwright.Page;
import com.microsoft.playwright.Playwright;
import java.util.Set;
import labexp.aceitacao.Base;
import labexp.aceitacao.p9.ServicoExternoStub.Modo;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/**
 * P9: sincronizacao com servico externo instavel.
 *
 * <p>Pre-requisito do ambiente: a aplicacao deve ter sido iniciada com
 * {@code NOTIFICACAO_URL=http://<host>:<STUB_PORTA>/notificacoes}. O estado da notificacao so e observavel
 * na tela ({@code status-notificacao}), por isso estes testes dirigem a interface.
 */
class P9NotificacaoTest extends Base {

    private static ServicoExternoStub stub;
    private static Playwright playwright;
    private static Browser browser;

    private Page page;

    @BeforeAll
    static void subir() {
        stub = new ServicoExternoStub();
        playwright = Playwright.create();
        browser = playwright.chromium().launch();
    }

    @AfterAll
    static void descer() {
        browser.close();
        playwright.close();
        stub.close();
    }

    @BeforeEach
    void abrirPagina() {
        stub.modo(Modo.OK_200);
        page = browser.newPage();
        page.onDialog(d -> d.accept());
    }

    @AfterEach
    void fecharPagina() {
        page.close();
        stub.modo(Modo.OK_200);
    }

    private Locator item(String titulo) {
        return page.getByTestId("tarefa-item").filter(new Locator.FilterOptions().setHasText(titulo));
    }

    /** O status pode ficar dentro do item da tarefa ou numa area unica da tela. */
    private Locator area(Locator item, String testid) {
        Locator dentro = item.getByTestId(testid);
        return dentro.count() > 0 ? dentro.first() : page.getByTestId(testid).first();
    }

    private String criarENavegar() {
        String titulo = tituloUnico("notif");
        assertEquals(201, api.criar(titulo, responsavelUnico(), FUTURO).status());
        page.navigate(BASE_URL);
        assertThat(item(titulo)).hasCount(1);
        return titulo;
    }

    private void concluirPelaTela(String titulo) {
        item(titulo).getByTestId("botao-concluir").click();
    }

    private String statusAte(String titulo, Set<String> esperados, long limiteMs) {
        long fim = System.currentTimeMillis() + limiteMs;
        String ultimo = "<area ausente>";
        while (System.currentTimeMillis() < fim) {
            Locator area = area(item(titulo), "status-notificacao");
            if (area.count() > 0) {
                ultimo = area.innerText().strip().toLowerCase();
                if (esperados.contains(ultimo)) {
                    return ultimo;
                }
            }
            page.waitForTimeout(100);
        }
        throw new AssertionError("status-notificacao esperado em " + esperados + " mas ficou em '" + ultimo + "'");
    }

    private String statusDaTarefa(String titulo) {
        for (var t : api.listar().json()) {
            if (t.get("titulo").asText().equals(titulo)) {
                return t.get("status").asText();
            }
        }
        throw new AssertionError("tarefa sumiu: " + titulo);
    }

    @Test
    void notificacaoEnviadaComSucesso() {
        stub.modo(Modo.OK_200);
        String titulo = criarENavegar();

        concluirPelaTela(titulo);

        assertEquals("enviada", statusAte(titulo, Set.of("enviada"), 5000));
        assertEquals("CONCLUIDA", statusDaTarefa(titulo));
        assertTrue(stub.requisicoes() >= 1, "a aplicacao nao chamou o servico externo (NOTIFICACAO_URL aponta para o stub?)");
    }

    @Test
    void notificacaoFalhoNaoImpedeConclusao() {
        stub.modo(Modo.ERRO_503);
        String titulo = criarENavegar();

        concluirPelaTela(titulo);

        assertEquals("falhou", statusAte(titulo, Set.of("falhou"), 5000));
        assertEquals("CONCLUIDA", statusDaTarefa(titulo));
        assertTrue(stub.requisicoes() >= 1, "a aplicacao nao chamou o servico externo (NOTIFICACAO_URL aponta para o stub?)");
    }

    @Test
    void timeoutNaoImpedeConclusao() {
        stub.modo(Modo.LENTO);
        String titulo = criarENavegar();

        long inicio = System.nanoTime();
        var resposta = page.waitForResponse(
                r -> r.request().method().equals("POST") && r.url().contains("/concluir"),
                () -> concluirPelaTela(titulo));
        long ms = (System.nanoTime() - inicio) / 1_000_000;

        assertEquals(200, resposta.status());
        assertTrue(ms < ServicoExternoStub.ATRASO_LENTO_MS - 500,
                "concluir levou " + ms + " ms: nao esperou so os 500 ms do limite, esperou o servico lento");
        String status = statusAte(titulo, Set.of("pendente", "falhou"), 5000);
        assertTrue(Set.of("pendente", "falhou").contains(status));
        assertEquals("CONCLUIDA", statusDaTarefa(titulo));
    }

    @Test
    void reenvioManualFunciona() {
        stub.modo(Modo.ERRO_503);
        String titulo = criarENavegar();
        concluirPelaTela(titulo);
        assertEquals("falhou", statusAte(titulo, Set.of("falhou"), 5000));
        int antes = stub.requisicoes();

        stub.modo(Modo.OK_200);
        Locator reenviar = area(item(titulo), "reenviar-notificacao");
        assertThat(reenviar).isVisible();
        reenviar.click();

        assertEquals("enviada", statusAte(titulo, Set.of("enviada"), 5000));
        assertTrue(stub.requisicoes() >= 1, "o reenvio nao chegou ao servico externo");
        assertTrue(antes >= 1);
    }
}
