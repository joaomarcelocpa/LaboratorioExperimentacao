package labexp.semente.domain;

import java.util.List;
import java.util.Map;

public record Relatorio(long pendentes, long concluidas, List<Tarefa> vencidas, Map<String, Long> porResponsavel) {
}
