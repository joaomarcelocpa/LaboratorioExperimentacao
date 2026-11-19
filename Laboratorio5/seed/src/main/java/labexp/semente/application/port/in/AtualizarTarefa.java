package labexp.semente.application.port.in;

import java.util.UUID;
import labexp.semente.domain.Tarefa;

public interface AtualizarTarefa {
    Tarefa atualizar(UUID id, DadosTarefa dados);
}
