package labexp.regressao;

import static com.microsoft.playwright.assertions.PlaywrightAssertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertEquals;

import com.microsoft.playwright.Browser;
import com.microsoft.playwright.Locator;
import com.microsoft.playwright.Page;
import com.microsoft.playwright.Playwright;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class TarefasUiTest extends Base {

    private static Playwright playwright;
    private static Browser browser;

    private Page page;
    private final AtomicInteger dialogos = new AtomicInteger();

    @BeforeAll
    static void abrirNavegador() {
        playwright = Playwright.create();
        browser = playwright.chromium().launch();
    }

    @AfterAll
    static void fecharNavegador() {
        browser.close();
        playwright.close();
    }

    @BeforeEach
    void abrirPagina() {
        page = browser.newPage();
        page.onDialog(d -> {
            dialogos.incrementAndGet();
            d.dismiss();
        });
        page.navigate(BASE_URL);
    }

    @AfterEach
    void fecharPagina() {
        page.close();
    }

    private Locator item(String responsavel) {
        return page.getByTestId("tarefa-item").filter(new Locator.FilterOptions().setHasText(responsavel));
    }

    private void preencher(String titulo, String responsavel) {
        page.getByTestId("form-titulo").fill(titulo);
        page.getByTestId("form-responsavel").fill(responsavel);
        page.getByTestId("form-vencimento").fill("2026-12-01T12:00");
    }

    private String criarPelaTela(String titulo) {
        String resp = responsavelUnico();
        preencher(titulo, resp);
        page.getByTestId("form-salvar").click();
        assertThat(item(resp)).hasCount(1);
        return resp;
    }

    @Test
    void criaTarefaPelaTelaEElaApareceNaLista() {
        String resp = criarPelaTela("Pagar conta");
        assertThat(item(resp).getByTestId("tarefa-titulo")).hasText("Pagar conta");
        assertThat(item(resp).getByTestId("tarefa-status")).hasText("PENDENTE");
    }

    @Test
    void editaTarefa() {
        String resp = criarPelaTela("Antes");
        item(resp).getByTestId("botao-editar").click();
        page.getByTestId("form-titulo").fill("Depois");
        page.getByTestId("form-salvar").click();
        assertThat(item(resp).getByTestId("tarefa-titulo")).hasText("Depois");
    }

    @Test
    void concluiTarefaEMostraStatus() {
        String resp = criarPelaTela("Concluir");
        item(resp).getByTestId("botao-concluir").click();
        assertThat(item(resp).getByTestId("tarefa-status")).hasText("CONCLUIDA");
    }

    @Test
    void excluiTarefaESomeDaLista() {
        String resp = criarPelaTela("Excluir");
        item(resp).getByTestId("botao-excluir").click();
        assertThat(item(resp)).hasCount(0);
    }

    @Test
    void tituloVazioMostraFormErro() {
        preencher("", responsavelUnico());
        page.getByTestId("form-salvar").click();
        assertThat(page.getByTestId("form-erro")).isVisible();
        assertThat(page.getByTestId("form-erro")).not().isEmpty();
    }

    @Test
    void tituloComHtmlApareceComoTexto() {
        String html = "<img src=x onerror=alert(1)>";
        String resp = criarPelaTela(html);
        assertThat(item(resp).getByTestId("tarefa-titulo")).hasText(html);
        assertEquals(0, dialogos.get());
    }
}
