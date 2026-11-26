package labexp.semente.application.port.in;

import java.time.Instant;

public record DadosTarefa(String titulo, String descricao, String responsavel, Instant vencimento) {
}
