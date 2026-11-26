package labexp.aceitacao.p4;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.microsoft.playwright.Browser;
import com.microsoft.playwright.Locator;
import com.microsoft.playwright.Page;
import com.microsoft.playwright.Playwright;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashSet;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.StreamSupport;
import labexp.aceitacao.Base;
import labexp.aceitacao.PapelNaTela;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/**
 * P4: importacao de tarefas via CSV. Fronteira: interface (importar-csv e resultado-importacao); o pedido nao
 * define rota HTTP. O CSV usa cabecalho titulo,responsavel,vencimento e vencimento ISO-8601 em UTC; o pedido
 * nao fixa o formato do vencimento nem se o cabecalho conta como linha (ver docs/s01/testes-p1-p4.md).
 */
class P4ImportacaoCsvTest extends Base {

    private static final int LINHAS = Integer.parseInt(System.getenv().getOrDefault("P4_LINHAS", "20000"));
    private static final int INVALIDAS = 50;

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
        page.navigate(BASE_URL);
        PapelNaTela.comoGestorSeExistir(page);
    }

    @AfterEach
    void fecharPagina() {
        page.close();
    }

    /** Linhas de dados (1-based) invalidas, espalhadas: alternam titulo ausente e vencimento fora do formato. */
    private static Set<Integer> invalidas(int linhas, int quantidade) {
        Set<Integer> r = new HashSet<>();
        int passo = Math.max(1, linhas / quantidade);
        for (int k = 0; k < quantidade; k++) {
            r.add(7 + k * passo > linhas ? linhas - k : 7 + k * passo);
        }
        return r;
    }

    private static Path escreverCsv(String responsavel, int linhas, Set<Integer> invalidas) throws IOException {
        StringBuilder sb = new StringBuilder("titulo,responsavel,vencimento\n");
        int k = 0;
        for (int j = 1; j <= linhas; j++) {
            if (invalidas.contains(j)) {
                sb.append(k++ % 2 == 0 ? "" : "invalida-" + j).append(',').append(responsavel).append(',')
                        .append(k % 2 == 1 ? "2099-01-01T12:00:00Z" : "amanha").append('\n');
            } else {
                sb.append("tarefa-").append(j).append(',').append(responsavel).append(",2099-01-01T12:00:00Z\n");
            }
        }
        Path arquivo = Files.createTempFile("p4-", ".csv");
        Files.writeString(arquivo, sb.toString());
        return arquivo;
    }

    private void importar(Path csv) {
        page.getByTestId("importar-csv").setInputFiles(csv);
        // "escolhe o arquivo e confirma": se houver botao de confirmacao, clica nele
        Locator confirmar = page.getByRole(com.microsoft.playwright.options.AriaRole.BUTTON,
                new Page.GetByRoleOptions().setName(Pattern.compile("importar|confirmar|enviar", Pattern.CASE_INSENSITIVE)));
        page.waitForTimeout(300);
        if (confirmar.count() > 0 && confirmar.first().isVisible()) {
            confirmar.first().click();
        }
    }

    private String aguardarResultado(String contem, long limiteMs) {
        Locator area = page.getByTestId("resultado-importacao");
        long fim = System.currentTimeMillis() + limiteMs;
        String texto = "";
        while (System.currentTimeMillis() < fim) {
            if (area.count() > 0) {
                texto = area.innerText();
                if (texto.replaceAll("[.,\\s]", "").contains(contem)) {
                    return texto;
                }
            }
            page.waitForTimeout(250);
        }
        throw new AssertionError("resultado-importacao nao mostrou '" + contem + "' em " + limiteMs + " ms; ultimo texto: "
                + texto.substring(0, Math.min(300, texto.length())));
    }

    private Set<Integer> linhasCitadas(String texto) {
        Set<Integer> r = new HashSet<>();
        Matcher m = Pattern.compile("(?i)linha\\D{0,3}(\\d+)").matcher(texto);
        while (m.find()) {
            r.add(Integer.parseInt(m.group(1)));
        }
        if (r.isEmpty()) { // formato sem a palavra "linha": usa todos os numeros que nao sejam os totais
            Matcher n = Pattern.compile("\\d+").matcher(texto.replaceAll("(?<=\\d)[.,](?=\\d{3})", ""));
            while (n.find()) {
                r.add(Integer.parseInt(n.group()));
            }
        }
        return r;
    }

    private long tarefasDe(String responsavel) {
        return StreamSupport.stream(api.listar().json().spliterator(), false)
                .filter(t -> t.get("responsavel").asText().equals(responsavel)).count();
    }

    @Test
    void importacaoContaCorretamenteErrosESucessos() throws IOException {
        String resp = responsavelUnico();
        Set<Integer> invalidas = invalidas(LINHAS, INVALIDAS);
        Path csv = escreverCsv(resp, LINHAS, invalidas);
        int esperadas = LINHAS - INVALIDAS;

        importar(csv);
        String texto = aguardarResultado(String.valueOf(esperadas), 180_000);

        Set<Integer> deDados = invalidas;
        Set<Integer> doArquivo = new HashSet<>();
        invalidas.forEach(j -> doArquivo.add(j + 1)); // o cabecalho e a linha 1 do arquivo
        Set<Integer> citadas = linhasCitadas(texto);
        citadas.removeAll(Set.of(esperadas, INVALIDAS, LINHAS, LINHAS + 1));
        assertTrue(citadas.equals(doArquivo) || citadas.equals(deDados),
                "esperava exatamente as " + INVALIDAS + " linhas invalidas (numeradas pelo arquivo ou pelos dados); veio "
                        + citadas.size() + " numeros: " + citadas);
        assertEquals(esperadas, tarefasDe(resp), "tarefas realmente criadas");
    }

    @Test
    void telaRespondeDuranteImportacao() throws IOException {
        String resp = responsavelUnico();
        String existente = api.criar(tituloUnico("existente"), responsavelUnico(), FUTURO).id();
        Path csv = escreverCsv(resp, LINHAS, invalidas(LINHAS, INVALIDAS));

        importar(csv);
        long fim = System.currentTimeMillis() + 3000;
        int consultas = 0;
        while (System.currentTimeMillis() < fim) {
            var r = api.consultar(existente);
            assertEquals(200, r.status());
            assertTrue(r.milissegundos() < 1500, "consulta levou " + r.milissegundos() + " ms durante a importacao");
            Locator campo = page.getByTestId("form-titulo");
            if (campo.count() > 0 && campo.isVisible()) {
                campo.fill("digitando-" + consultas);
                assertEquals("digitando-" + consultas, campo.inputValue(), "a tela nao respondeu durante a importacao");
            }
            consultas++;
        }
        assertTrue(consultas > 0);
        aguardarResultado(String.valueOf(LINHAS - INVALIDAS), 180_000);
    }

    @Test
    void linhasInvalidasNaoGeramTarefasParciais() throws IOException {
        String resp = responsavelUnico();
        Set<Integer> invalidas = invalidas(100, 7);
        Path csv = escreverCsv(resp, 100, invalidas);

        importar(csv);
        aguardarResultado("93", 60_000);

        assertEquals(93, tarefasDe(resp), "so as validas foram salvas");
        boolean parcial = StreamSupport.stream(api.listar().json().spliterator(), false)
                .anyMatch(t -> t.get("titulo").asText().startsWith("invalida-")
                        && t.get("responsavel").asText().equals(resp));
        assertTrue(!parcial, "linha com vencimento invalido virou tarefa parcial");
    }
}
