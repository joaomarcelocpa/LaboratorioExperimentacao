package labexp.aceitacao.p6;

import static com.microsoft.playwright.assertions.PlaywrightAssertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.microsoft.playwright.Browser;
import com.microsoft.playwright.Locator;
import com.microsoft.playwright.Page;
import com.microsoft.playwright.Playwright;
import labexp.aceitacao.ApiClient;
import labexp.aceitacao.ApiClient.Resposta;
import labexp.aceitacao.Base;
import labexp.aceitacao.PapelNaTela;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/** P6: permissoes por papel. Fronteira: HTTP (X-Papel) e interface (papel-usuario e botoes). */
class P6PapelTest extends Base {

    private static Playwright playwright;
    private static Browser browser;

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

    private void verificarRestricoes(ApiClient cliente, String rotulo) {
        String resp = responsavelUnico();
        String id = api.criar("Existente", resp, FUTURO).id();

        Resposta criar = cliente.criar("Nova", resp, FUTURO);
        assertEquals(403, criar.status(), rotulo + " criar: " + criar.corpo());
        Resposta atualizar = cliente.atualizar(id, "Alterada", resp, FUTURO);
        assertEquals(403, atualizar.status(), rotulo + " atualizar: " + atualizar.corpo());
        Resposta excluir = cliente.excluir(id);
        assertEquals(403, excluir.status(), rotulo + " excluir: " + excluir.corpo());

        // as operacoes negadas nao tiveram efeito
        assertEquals("Existente", api.consultar(id).json().get("titulo").asText());
        long total = java.util.stream.StreamSupport.stream(api.listar().json().spliterator(), false)
                .filter(t -> t.get("responsavel").asText().equals(resp)).count();
        assertEquals(1, total, rotulo + ": a criacao negada nao pode gerar tarefa");

        // concluir e permitido a todos
        Resposta concluir = cliente.concluir(id);
        assertEquals(200, concluir.status(), rotulo + " concluir: " + concluir.corpo());
        assertEquals("CONCLUIDA", concluir.json().get("status").asText());
    }

    @Test
    void gestor_pode_executar_todas_operacoes() {
        String resp = responsavelUnico();
        Resposta criada = api.criar("Gestao", resp, FUTURO);
        assertEquals(201, criada.status(), criada.corpo());
        String id = criada.id();

        assertEquals(200, api.atualizar(id, "Gestao 2", resp, FUTURO).status());
        assertEquals(200, api.concluir(id).status());
        assertEquals(204, api.excluir(id).status());
    }

    @Test
    void colaborador_recebe_403_em_operacoes_restritas() {
        verificarRestricoes(api.papel("colaborador"), "colaborador");
    }

    @Test
    void sem_cabecalho_usa_papel_colaborador() {
        verificarRestricoes(api.papel(null), "sem cabecalho");
    }

    @Test
    void interface_mostra_papel_e_oculta_botoes_para_colaborador() {
        String resp = responsavelUnico();
        api.criar("Visivel", resp, FUTURO);

        Page page = browser.newPage();
        try {
            page.navigate(BASE_URL);
            Locator campo = page.getByTestId("papel-usuario");
            assertThat(campo).isVisible();
            assertEquals("colaborador", PapelNaTela.valor(campo), "sem escolha explicita o papel ativo e colaborador");

            Locator item = page.getByTestId("tarefa-item").filter(new Locator.FilterOptions().setHasText(resp));
            assertThat(item).hasCount(1);
            assertThat(item.getByTestId("botao-editar")).hasCount(0);
            assertThat(item.getByTestId("botao-excluir")).hasCount(0);
            assertThat(page.getByTestId("form-salvar")).not().isVisible();
            assertThat(item.getByTestId("botao-concluir")).isVisible();
        } finally {
            page.close();
        }
    }

    @Test
    void interface_exibe_botoes_para_gestor() {
        String resp = responsavelUnico();
        api.criar("Visivel", resp, FUTURO);

        Page page = browser.newPage();
        try {
            page.navigate(BASE_URL);
            PapelNaTela.definir(page, "gestor");
            assertEquals("gestor", PapelNaTela.valor(page.getByTestId("papel-usuario")));

            Locator item = page.getByTestId("tarefa-item").filter(new Locator.FilterOptions().setHasText(resp));
            assertThat(item).hasCount(1);
            assertThat(item.getByTestId("botao-editar")).isVisible();
            assertThat(item.getByTestId("botao-excluir")).isVisible();
            assertThat(page.getByTestId("form-salvar")).isVisible();
            assertTrue(item.getByTestId("botao-concluir").isVisible());
        } finally {
            page.close();
        }
    }
}
