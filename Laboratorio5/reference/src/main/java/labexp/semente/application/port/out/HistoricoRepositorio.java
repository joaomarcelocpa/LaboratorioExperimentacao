package labexp.semente.application.port.out;

import java.util.List;
import java.util.UUID;
import labexp.semente.domain.AlteracaoTarefa;

public interface HistoricoRepositorio {
    void registrar(List<AlteracaoTarefa> alteracoes);

    /** Da mais recente para a mais antiga. */
    List<AlteracaoTarefa> listar(UUID tarefaId);
}
