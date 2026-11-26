package labexp.aceitacao.p3;

import static com.microsoft.playwright.assertions.PlaywrightAssertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.microsoft.playwright.Browser;
import com.microsoft.playwright.Locator;
import com.microsoft.playwright.Page;
import com.microsoft.playwright.Playwright;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.stream.StreamSupport;
import labexp.aceitacao.ApiClient;
import labexp.aceitacao.ApiClient.Resposta;
import labexp.aceitacao.Base;
import labexp.aceitacao.PapelNaTela;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/** P3: isolamento por empresa. Fronteira: HTTP (X-Empresa) e interface (empresa-input). */
class P3EmpresaTest extends Base {

    private static Playwright playwright;
    private static Browser browser;

    private final List<Runnable> limpezas = new ArrayList<>();

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

    @AfterEach
    void limparEmpresas() {
        limpezas.forEach(Runnable::run);
    }

    private ApiClient empresa(String rotulo) {
        String nome = rotulo + "-" + UUID.randomUUID().toString().substring(0, 8);
        ApiClient c = api.empresa(nome);
        limpezas.add(() -> StreamSupport.stream(c.listar().json().spliterator(), false)
                .forEach(t -> c.excluir(t.get("id").asText())));
        return c;
    }

    private static long contar(ApiClient c, String responsavel) {
        return StreamSupport.stream(c.listar().json().spliterator(), false)
                .filter(t -> t.get("responsavel").asText().equals(responsavel)).count();
    }

    @Test
    void empresaBNaoVeTarefasDaEmpresaA() {
        ApiClient a = empresa("A");
        ApiClient b = empresa("B");
        String resp = "p3-" + UUID.randomUUID();
        for (int i = 0; i < 3; i++) {
            assertEquals(201, a.criar("da-A-" + i, resp, FUTURO).status());
        }

        assertEquals(3, contar(a, resp), "a empresa A ve as proprias tarefas");
        Resposta listaB = b.listar();
        assertEquals(200, listaB.status());
        assertEquals(0, contar(b, resp), "a empresa B nao ve tarefas da A");
        assertEquals(0, listaB.json().size(), "a empresa B e nova: lista vazia");
    }

    @Test
    void empresaBRecebe404AoAcessarTarefaDaEmpresaA() {
        ApiClient a = empresa("A");
        ApiClient b = empresa("B");
        String resp = "p3-" + UUID.randomUUID();
        String id = a.criar("so-da-A", resp, FUTURO).id();

        assertEquals(404, b.consultar(id).status());
        assertEquals(404, b.atualizar(id, "invadida", resp, FUTURO).status());
        assertEquals(404, b.excluir(id).status());

        Resposta intacta = a.consultar(id);
        assertEquals(200, intacta.status(), "a tarefa continua existindo para a dona");
        assertEquals("so-da-A", intacta.json().get("titulo").asText(), "a tentativa de B nao alterou a tarefa");
    }

    @Test
    void tarefasAntigasVisiveisNaEmpresaPadrao() {
        // "antigas" = criadas sem identificar empresa; a empresa padrao e a de quem nao envia o cabecalho
        String resp = responsavelUnico();
        String id = api.criar("antiga", resp, FUTURO).id();
        ApiClient semEmpresa = api;

        assertEquals(1, contar(semEmpresa, resp));
        assertEquals(200, semEmpresa.consultar(id).status());
        ApiClient outra = empresa("X");
        assertEquals(404, outra.consultar(id).status(), "tarefa da empresa padrao nao vaza para outra empresa");
    }

    @Test
    void semCabecalhoFuncionaComoAntes() {
        String resp = responsavelUnico();
        Resposta criada = api.criar("ciclo", resp, FUTURO);
        assertEquals(201, criada.status(), criada.corpo());
        String id = criada.id();
        assertEquals(200, api.atualizar(id, "ciclo 2", resp, FUTURO).status());
        assertEquals(200, api.concluir(id).status());
        assertEquals(200, api.consultar(id).status());
        assertEquals(204, api.excluir(id).status());
        assertEquals(404, api.consultar(id).status());
    }

    @Test
    void interfaceIsolaPorEmpresa() {
        String nomeA = "ui-A-" + UUID.randomUUID().toString().substring(0, 8);
        String nomeB = "ui-B-" + UUID.randomUUID().toString().substring(0, 8);
        limpezas.add(() -> {
            for (String n : List.of(nomeA, nomeB)) {
                ApiClient c = api.empresa(n);
                StreamSupport.stream(c.listar().json().spliterator(), false)
                        .forEach(t -> c.excluir(t.get("id").asText()));
            }
        });
        String resp = "p3ui-" + UUID.randomUUID();
        String titulo = tituloUnico("ui");

        Page page = browser.newPage();
        try {
            page.navigate(BASE_URL);
            PapelNaTela.comoGestorSeExistir(page);
            Locator campo = page.getByTestId("empresa-input");
            assertThat(campo).isVisible();

            definirEmpresa(page, nomeA);
            page.getByTestId("form-titulo").fill(titulo);
            page.getByTestId("form-responsavel").fill(resp);
            page.getByTestId("form-vencimento").fill("2099-12-01T12:00");
            page.getByTestId("form-salvar").click();
            Locator itemA = page.getByTestId("tarefa-item").filter(new Locator.FilterOptions().setHasText(resp));
            assertThat(itemA).hasCount(1);
            assertEquals(1, contar(api.empresa(nomeA), resp), "a tarefa criada pela tela pertence a empresa informada");
            assertEquals(0, contar(api.empresa(nomeB), resp));

            definirEmpresa(page, nomeB);
            assertThat(page.getByTestId("tarefa-item").filter(new Locator.FilterOptions().setHasText(resp))).hasCount(0);

            definirEmpresa(page, nomeA);
            assertThat(page.getByTestId("tarefa-item").filter(new Locator.FilterOptions().setHasText(resp))).hasCount(1);
        } finally {
            page.close();
        }
        assertTrue(true);
    }

    private static void definirEmpresa(Page page, String nome) {
        Locator campo = page.getByTestId("empresa-input");
        campo.fill(nome);
        campo.press("Enter");
        campo.blur();
        page.waitForTimeout(500);
    }
}
