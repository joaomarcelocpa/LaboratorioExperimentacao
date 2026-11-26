package labexp.semente.domain;

import java.time.Instant;
import java.util.UUID;

public record Aviso(UUID tarefaId, String titulo, Instant vencidaEm, Instant criadoEm) {
}
