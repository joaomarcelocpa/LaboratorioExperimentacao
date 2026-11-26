package labexp.semente.domain;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.time.Instant;
import org.junit.jupiter.api.Test;

class TarefaTest {

    private static final Instant VENC = Instant.parse("2026-12-01T15:00:00Z");

    @Test
    void criaTarefaPendenteComIdECriadaEm() {
        Tarefa t = Tarefa.nova("Pagar", null, "ana", VENC);
        assertEquals(StatusTarefa.PENDENTE, t.status());
        assertNotNull(t.id());
        assertNotNull(t.criadaEm());
    }

    @Test
    void rejeitaTituloVazioOuSoEspacos() {
        for (String titulo : new String[] {"", "   ", null}) {
            assertThrows(TarefaInvalidaException.class, () -> Tarefa.nova(titulo, null, "ana", VENC));
        }
    }

    @Test
    void rejeitaTitulo121Caracteres() {
        assertThrows(TarefaInvalidaException.class, () -> Tarefa.nova("a".repeat(121), null, "ana", VENC));
    }

    @Test
    void aceitaTitulo120Caracteres() {
        assertEquals(120, Tarefa.nova("a".repeat(120), null, "ana", VENC).titulo().length());
    }

    @Test
    void rejeitaResponsavelVazioOuLongoDemais() {
        assertThrows(TarefaInvalidaException.class, () -> Tarefa.nova("t", null, " ", VENC));
        assertThrows(TarefaInvalidaException.class, () -> Tarefa.nova("t", null, "r".repeat(81), VENC));
    }

    @Test
    void rejeitaDescricaoComMaisDe2000() {
        assertThrows(TarefaInvalidaException.class, () -> Tarefa.nova("t", "d".repeat(2001), "ana", VENC));
    }

    @Test
    void rejeitaVencimentoNulo() {
        assertThrows(TarefaInvalidaException.class, () -> Tarefa.nova("t", null, "ana", null));
    }

    @Test
    void truncaInstantesParaMicrossegundos() {
        Instant comNanos = Instant.parse("2026-12-01T15:00:00.123456789Z");
        Tarefa t = Tarefa.nova("t", null, "ana", comNanos);
        assertEquals(Instant.parse("2026-12-01T15:00:00.123456Z"), t.vencimento());
        assertEquals(0, t.criadaEm().getNano() % 1000);
    }

    @Test
    void atualizadaPreservaIdStatusECriadaEm() {
        Tarefa t = Tarefa.nova("t", null, "ana", VENC).concluida();
        Tarefa a = t.atualizada("novo", "desc", "bia", VENC.plusSeconds(60));
        assertEquals(t.id(), a.id());
        assertEquals(t.status(), a.status());
        assertEquals(t.criadaEm(), a.criadaEm());
        assertEquals("novo", a.titulo());
        assertEquals("bia", a.responsavel());
    }

    @Test
    void concluidaMudaStatusEEhIdempotente() {
        Tarefa t = Tarefa.nova("t", null, "ana", VENC);
        assertEquals(StatusTarefa.CONCLUIDA, t.concluida().status());
        assertEquals(t.concluida(), t.concluida().concluida());
    }
}
