package labexp.aceitacao.p5;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.fasterxml.jackson.databind.JsonNode;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import labexp.aceitacao.Base;
import labexp.aceitacao.Json;
import org.junit.jupiter.api.Test;

/** P5: historico de alteracoes. Fronteira: HTTP (GET /tarefas/{id}/historico). */
class P5HistoricoTest extends Base {

    private static String campo(JsonNode entrada) {
        return Json.texto(Json.campo(entrada, "campo", "field", "atributo", "propriedade")
                .orElseThrow(() -> new AssertionError("entrada sem campo alterado: " + entrada)));
    }

    private static String anterior(JsonNode entrada) {
        return Json.texto(Json.campo(entrada, "valorAnterior", "anterior", "valorAntigo", "valorAntes", "de", "from",
                "oldValue").or(() -> Json.campoContendo(entrada, "anterior", "antigo", "antes", "old", "prev"))
                .orElseThrow(() -> new AssertionError("entrada sem valor anterior: " + entrada)));
    }

    private static String novo(JsonNode entrada) {
        return Json.texto(Json.campo(entrada, "valorNovo", "novo", "valorDepois", "para", "to", "newValue")
                .or(() -> Json.campoContendo(entrada, "novo", "nova", "depois", "new"))
                .orElseThrow(() -> new AssertionError("entrada sem valor novo: " + entrada)));
    }

    private static Instant momento(JsonNode entrada) {
        JsonNode n = Json.campo(entrada, "timestamp", "momento", "alteradoEm", "dataHora", "data", "criadoEm", "quando",
                "instante", "ocorridoEm", "em").orElseGet(() -> {
                    for (JsonNode v : entrada) {
                        if (Json.pareceTimestamp(v)) {
                            return v;
                        }
                    }
                    throw new AssertionError("entrada sem timestamp: " + entrada);
                });
        return Json.instante(n);
    }

    private List<JsonNode> historico(String id) {
        var r = api.get("/tarefas/" + id + "/historico");
        assertEquals(200, r.status(), r.corpo());
        return Json.itens(r.json());
    }

    @Test
    void historico_registra_alteracoes_com_metadados() {
        String r1 = responsavelUnico();
        String r2 = responsavelUnico();
        String id = api.criar("Titulo original", r1, FUTURO).id();
        Instant antes = Instant.now().minusSeconds(60);

        assertEquals(200, api.atualizar(id, "Titulo novo", r1, FUTURO).status());
        assertEquals(200, api.atualizar(id, "Titulo novo", r2, FUTURO).status());

        List<JsonNode> entradas = historico(id);
        assertEquals(2, entradas.size(), "criar nao e alteracao; duas atualizacoes de um campo cada: " + entradas);

        // ordem cronologica inversa: a mais recente (responsavel) vem primeiro
        assertEquals("responsavel", campo(entradas.get(0)).toLowerCase());
        assertEquals(r1, anterior(entradas.get(0)));
        assertEquals(r2, novo(entradas.get(0)));
        assertEquals("titulo", campo(entradas.get(1)).toLowerCase());
        assertEquals("Titulo original", anterior(entradas.get(1)));
        assertEquals("Titulo novo", novo(entradas.get(1)));

        Instant recente = momento(entradas.get(0));
        Instant antiga = momento(entradas.get(1));
        assertFalse(recente.isBefore(antiga), "ordem cronologica inversa");
        assertTrue(antiga.isAfter(antes) && recente.isBefore(Instant.now().plusSeconds(60)),
                "timestamp deve refletir o momento da alteracao");
    }

    @Test
    void historico_registra_conclusao() {
        String id = api.criar(tituloUnico("concluir"), responsavelUnico(), FUTURO).id();
        assertEquals(200, api.concluir(id).status());

        List<JsonNode> entradas = historico(id);
        assertEquals(1, entradas.size(), entradas.toString());
        JsonNode e = entradas.get(0);
        assertEquals("status", campo(e).toLowerCase());
        assertEquals("PENDENTE", anterior(e).toUpperCase());
        assertEquals("CONCLUIDA", novo(e).toUpperCase());
        assertNotNull(momento(e));
    }

    @Test
    void historico_tarefa_inexistente_retorna_404() {
        assertEquals(404, api.get("/tarefas/" + UUID.randomUUID() + "/historico").status());
    }

    @Test
    void historico_persiste_apos_exclusao() throws InterruptedException {
        String resp = responsavelUnico();
        String id = api.criar("Antes", resp, FUTURO).id();
        assertEquals(200, api.atualizar(id, "Depois", resp, FUTURO).status());
        assertEquals(204, api.excluir(id).status());

        // o texto exige o historico por "pelo menos 1 segundo" apos excluir: le logo apos e perto do limite
        assertEquals(1, historico(id).size(), "historico some logo apos a exclusao");
        Thread.sleep(900);
        List<JsonNode> depois = historico(id);
        assertEquals(1, depois.size(), "historico some antes de 1 segundo");
        assertEquals("titulo", campo(depois.get(0)).toLowerCase());
    }
}
