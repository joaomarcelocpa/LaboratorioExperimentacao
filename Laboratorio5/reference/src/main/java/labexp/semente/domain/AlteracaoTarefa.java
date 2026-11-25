package labexp.semente.domain;

import java.time.Instant;
import java.util.UUID;

public record AlteracaoTarefa(UUID tarefaId, String campo, String valorAnterior, String valorNovo, Instant momento) {
}
