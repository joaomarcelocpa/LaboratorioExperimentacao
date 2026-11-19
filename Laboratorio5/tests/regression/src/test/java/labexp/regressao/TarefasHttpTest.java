package labexp.regressao;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.stream.StreamSupport;
import labexp.regressao.ApiClient.Resposta;
import org.junit.jupiter.api.Test;

class TarefasHttpTest extends Base {

    private void erro(Resposta r, int status, String codigo) {
        assertEquals(status, r.status(), r.corpo());
        assertEquals(codigo, r.json().get("erro").asText());
        assertFalse(r.json().get("mensagem").asText().isBlank());
    }

    @Test
    void cicloCompletoDeUmaTarefa() {
        String resp = responsavelUnico();
        Resposta criada = api.criar("Pagar conta", resp, VENCIMENTO);
        assertEquals(201, criada.status());
        assertEquals("PENDENTE", criada.json().get("status").asText());
        String id = criada.id();

        Resposta lida = api.consultar(id);
        assertEquals(200, lida.status());
        assertEquals("Pagar conta", lida.json().get("titulo").asText());
        assertEquals(VENCIMENTO, lida.json().get("vencimento").asText());

        Resposta atualizada = api.atualizar(id, "Pagar luz", resp, "2026-12-02T15:00:00Z");
        assertEquals(200, atualizada.status());
        assertEquals("Pagar luz", atualizada.json().get("titulo").asText());

        Resposta concluida = api.concluir(id);
        assertEquals(200, concluida.status());
        assertEquals("CONCLUIDA", concluida.json().get("status").asText());

        assertEquals(204, api.excluir(id).status());
        assertEquals(404, api.consultar(id).status());
    }

    @Test
    void listaContemTarefaCriada() {
        String id = api.criar("Listada", responsavelUnico(), VENCIMENTO).id();
        boolean achou = StreamSupport.stream(api.listar().json().spliterator(), false)
                .anyMatch(t -> t.get("id").asText().equals(id));
        assertTrue(achou);
    }

    @Test
    void atualizarNaoMudaStatus() {
        String resp = responsavelUnico();
        String id = api.criar("a", resp, VENCIMENTO).id();
        api.concluir(id);
        Resposta r = api.atualizar(id, "b", resp, VENCIMENTO);
        assertEquals("CONCLUIDA", r.json().get("status").asText());
    }

    @Test
    void tituloVazioOuSoEspacosDa400() {
        String resp = responsavelUnico();
        erro(api.criar("", resp, VENCIMENTO), 400, "requisicao_invalida");
        erro(api.criar("   ", resp, VENCIMENTO), 400, "requisicao_invalida");
    }

    @Test
    void titulo121Da400() {
        erro(api.criar("a".repeat(121), responsavelUnico(), VENCIMENTO), 400, "requisicao_invalida");
    }

    @Test
    void titulo120Da201() {
        assertEquals(201, api.criar("a".repeat(120), responsavelUnico(), VENCIMENTO).status());
    }

    @Test
    void vencimentoAusenteDa400() {
        erro(api.criar("t", responsavelUnico(), null), 400, "requisicao_invalida");
    }

    @Test
    void vencimentoInvalidoDa400() {
        erro(api.criar("t", responsavelUnico(), "amanha"), 400, "requisicao_invalida");
    }

    @Test
    void jsonMalformadoDa400() {
        erro(api.enviar("POST", "/tarefas", "{nao e json"), 400, "requisicao_invalida");
    }

    @Test
    void corpoVazioDa400() {
        erro(api.enviar("POST", "/tarefas", ""), 400, "requisicao_invalida");
    }

    @Test
    void idMalformadoDa404EmTodasAsRotas() {
        String corpo = ApiClient.corpo("t", null, "ana", VENCIMENTO);
        erro(api.enviar("GET", "/tarefas/nao-e-uuid", null), 404, "nao_encontrada");
        erro(api.enviar("PUT", "/tarefas/nao-e-uuid", corpo), 404, "nao_encontrada");
        erro(api.enviar("POST", "/tarefas/nao-e-uuid/concluir", null), 404, "nao_encontrada");
        erro(api.enviar("DELETE", "/tarefas/nao-e-uuid", null), 404, "nao_encontrada");
    }

    @Test
    void idInexistenteDa404() {
        erro(api.consultar("00000000-0000-0000-0000-000000000000"), 404, "nao_encontrada");
    }

    @Test
    void vencimentoComOffsetVoltaEmUtc() {
        Resposta r = api.criar("t", responsavelUnico(), "2026-12-01T12:00:00-03:00");
        assertEquals(201, r.status());
        assertEquals("2026-12-01T15:00:00Z", r.json().get("vencimento").asText());
    }

    @Test
    void concluirDuasVezesDa200() {
        String id = api.criar("t", responsavelUnico(), VENCIMENTO).id();
        assertEquals(200, api.concluir(id).status());
        assertEquals(200, api.concluir(id).status());
    }

    @Test
    void excluirDuasVezesDa404NaSegunda() {
        String id = api.criar("t", responsavelUnico(), VENCIMENTO).id();
        assertEquals(204, api.excluir(id).status());
        assertEquals(404, api.excluir(id).status());
    }

    @Test
    void healthResponde200() {
        assertEquals(200, api.enviar("GET", "/health", null).status());
    }
}
