package labexp.aceitacao.p1;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.microsoft.playwright.Browser;
import com.microsoft.playwright.Locator;
import com.microsoft.playwright.Page;
import com.microsoft.playwright.Playwright;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import labexp.aceitacao.Base;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/**
 * P1: aviso de vencimento. Fronteira: interface (data-testid="lista-avisos"). O pedido nao define rota HTTP
 * para os avisos, entao so a tela e observavel. Tarefas sao criadas pela API (carga conforme o contrato).
 */
class P1AvisosTest extends Base {

    private static Playwright playwright;
    private static Browser browser;
    private Page page;

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
    }

    @AfterEach
    void fecharPagina() {
        page.close();
    }

    /** A tela de Avisos pode ser a propria pagina ou ficar atras de um link/botao "Avisos". */
    private Locator abrirAvisos() {
        page.navigate(BASE_URL);
        Locator lista = page.getByTestId("lista-avisos");
        if (lista.count() == 0 || !lista.first().isVisible()) {
            Locator acesso = page.getByText(java.util.regex.Pattern.compile("avisos", java.util.regex.Pattern.CASE_INSENSITIVE))
                    .filter(new Locator.FilterOptions().setHasNot(page.getByTestId("lista-avisos")));
            if (acesso.count() > 0) {
                acesso.first().click();
            }
        }
        lista = page.getByTestId("lista-avisos");
        lista.first().waitFor(new Locator.WaitForOptions().setTimeout(5000));
        return lista.first();
    }

    private String textoDosAvisos() {
        return abrirAvisos().innerText();
    }

    private int ocorrencias(String texto, String trecho) {
        int n = 0;
        for (int i = texto.indexOf(trecho); i >= 0; i = texto.indexOf(trecho, i + 1)) {
            n++;
        }
        return n;
    }

    /** Espera, recarregando a tela, ate o titulo aparecer ou o limite passar. */
    private boolean apareceAte(String titulo, Instant limite) throws InterruptedException {
        while (Instant.now().isBefore(limite)) {
            if (textoDosAvisos().contains(titulo)) {
                return true;
            }
            Thread.sleep(1500);
        }
        return textoDosAvisos().contains(titulo);
    }

    @Test
    void avisoApareceDentroDoTempoAposVencimento() throws InterruptedException {
        String titulo = tituloUnico("aviso");
        Instant vencimento = Instant.now().plusSeconds(5).truncatedTo(ChronoUnit.MILLIS);
        assertEquals(201, api.criar(titulo, responsavelUnico(), vencimento.toString()).status());

        assertTrue(apareceAte(titulo, vencimento.plusSeconds(30)),
                "o aviso nao apareceu em ate 30 s depois do vencimento");
    }

    @Test
    void tarefaConcluidaNaoGeraAviso() throws InterruptedException {
        String resp = responsavelUnico();
        String concluida = tituloUnico("concluida");
        String controle = tituloUnico("controle");
        Instant vencimento = Instant.now().plusSeconds(4).truncatedTo(ChronoUnit.MILLIS);
        String idConcluida = api.criar(concluida, resp, vencimento.toString()).id();
        assertEquals(201, api.criar(controle, resp, vencimento.toString()).status());
        assertEquals(200, api.concluir(idConcluida).status());

        // o controle vence junto e nao foi concluido: quando o aviso dele aparece, o da concluida ja teria aparecido
        assertTrue(apareceAte(controle, vencimento.plusSeconds(30)), "o mecanismo de avisos nao funcionou para o controle");
        Thread.sleep(2000);
        assertFalse(textoDosAvisos().contains(concluida), "tarefa concluida antes do vencimento gerou aviso");
    }

    @Test
    void tarefaGeraNoMaximoUmAviso() throws InterruptedException {
        String titulo = tituloUnico("unico");
        Instant vencimento = Instant.now().plusSeconds(3).truncatedTo(ChronoUnit.MILLIS);
        assertEquals(201, api.criar(titulo, responsavelUnico(), vencimento.toString()).status());
        assertTrue(apareceAte(titulo, vencimento.plusSeconds(30)));

        for (int i = 0; i < 4; i++) {
            Thread.sleep(1500);
            assertEquals(1, ocorrencias(textoDosAvisos(), titulo), "consulta " + (i + 1) + " da tela de avisos");
        }
    }
}
