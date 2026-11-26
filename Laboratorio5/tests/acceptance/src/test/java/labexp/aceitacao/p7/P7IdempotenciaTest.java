package labexp.aceitacao.p7;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.util.stream.StreamSupport;
import labexp.aceitacao.ApiClient.Resposta;
import labexp.aceitacao.Base;
import org.junit.jupiter.api.Test;

/** P7: reenvio sem duplicar. Fronteira: HTTP (cabecalho Idempotency-Key). */
class P7IdempotenciaTest extends Base {

    private long contar(String responsavel) {
        return StreamSupport.stream(api.listar().json().spliterator(), false)
                .filter(t -> t.get("responsavel").asText().equals(responsavel)).count();
    }

    @Test
    void reenvioComMesmaChaveNaoDuplica() {
        String resp = responsavelUnico();
        String chave = "chave-" + java.util.UUID.randomUUID();

        Resposta primeira = api.criarComChave(chave, "Pagar", resp, FUTURO);
        Resposta segunda = api.criarComChave(chave, "Pagar", resp, FUTURO);

        assertEquals(201, primeira.status(), primeira.corpo());
        assertEquals(201, segunda.status(), segunda.corpo());
        assertEquals(primeira.json(), segunda.json(), "o reenvio devolve a resposta original");
        assertEquals(1, contar(resp));
    }

    @Test
    void chaveComPayloadDiferenteRetorna422() {
        String resp = responsavelUnico();
        String chave = "chave-" + java.util.UUID.randomUUID();

        assertEquals(201, api.criarComChave(chave, "Pagar", resp, FUTURO).status());
        Resposta conflito = api.criarComChave(chave, "Outro titulo", resp, FUTURO);

        assertEquals(422, conflito.status(), conflito.corpo());
        assertEquals(1, contar(resp), "o conflito nao pode criar tarefa");
    }

    @Test
    void semChaveIdempotenciaFuncionaNormal() {
        String resp = responsavelUnico();

        Resposta a = api.criar("Pagar", resp, FUTURO);
        Resposta b = api.criar("Pagar", resp, FUTURO);

        assertEquals(201, a.status());
        assertEquals(201, b.status());
        assertEquals(2, contar(resp), "sem chave nao ha garantia de idempotencia: cada envio cria uma tarefa");
    }

    @Test
    void listagemConfirmaUnicaTarefaAposReenvio() {
        String resp = responsavelUnico();
        String chave = "chave-" + java.util.UUID.randomUUID();

        for (int i = 0; i < 3; i++) {
            assertEquals(201, api.criarComChave(chave, "Reenviada", resp, FUTURO).status());
        }

        assertEquals(1, contar(resp));
    }
}
